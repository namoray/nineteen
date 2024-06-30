import asyncio
import collections
import random
from typing import AsyncGenerator, Dict, List, Union

from fastapi.responses import JSONResponse
from pydantic import BaseModel
from core import Task, bittensor_overrides as bto
import bittensor as bt
from validation.models import UIDRecord, axon_uid
from validation.synthetic_data import synthetic_generations
from core import tasks, constants as core_cst
from validation.proxy.utils import query_utils
from models import base_models, utility_models
from validation.db.db_management import db_manager

# LLM VOLUMES ARE IN TOKENS,
# IMAGE VOLUMES ARE IN STEP
# CLIP IS IN IMAGES
TASK_TO_VOLUME_TO_REQUESTS_CONVERSION: Dict[Task, float] = {
    Task.chat_llama_3: 300,
    Task.chat_mixtral: 300,
    Task.proteus_text_to_image: 10,
    Task.playground_text_to_image: 50,
    Task.dreamshaper_text_to_image: 10,
    Task.proteus_image_to_image: 10,
    Task.playground_image_to_image: 50,
    Task.dreamshaper_image_to_image: 10,
    Task.jugger_inpainting: 20,
    Task.avatar: 10,
    Task.clip_image_embeddings: 1,
}


async def _async_chain(first_chunk, async_gen):
    yield first_chunk
    async for item in async_gen:
        yield item


class UidManager:
    def __init__(
        self,
        capacities_for_tasks: Dict[Task, Dict[axon_uid, float]],
        dendrite: bt.dendrite,
        validator_hotkey: str,
        uid_to_uid_info: Dict[axon_uid, utility_models.UIDinfo],
        synthetic_data_manager: synthetic_generations.SyntheticDataManager,
        is_testnet: bool,
    ) -> None:
        self.capacities_for_tasks = capacities_for_tasks
        self.dendrite = dendrite
        self.validator_hotkey = validator_hotkey
        self.uid_to_axon: Dict[axon_uid, bto.axon] = {info.uid: info.axon for info in uid_to_uid_info.values()}

        self.uid_records_for_tasks: Dict[Task, Dict[axon_uid, UIDRecord]] = collections.defaultdict(dict)
        self.synthetic_scoring_tasks: List[asyncio.Task] = []
        self.task_to_uid_queue: Dict[Task, query_utils.UIDQueue] = {}
        self.synthetic_data_manager = synthetic_data_manager

        self.is_testnet = is_testnet

    def calculate_period_scores_for_uids(self) -> None:
        for task in self.uid_records_for_tasks:
            for record in self.uid_records_for_tasks[task].values():
                record.calculate_period_score()

    async def store_period_scores(self) -> None:
        for uid_records in self.uid_records_for_tasks.values():
            for uid_record in uid_records.values():
                await db_manager.insert_uid_record(uid_record, self.validator_hotkey)

    # this needs refactoring to not be a bunch of asyncio tasks which is very prone to errors
    # And problems, but instead just be one
    async def start_synthetic_scoring(self) -> None:
        self.synthetic_scoring_tasks = []
        for task in Task:
            self.task_to_uid_queue[task] = query_utils.UIDQueue()
            for uid, volume in self.capacities_for_tasks.get(task, {}).items():
                # Need to add before start synthetic scoring so we can query the uid
                volume_to_score = volume * self._get_percentage_of_tasks_to_score()
                if volume_to_score == 0:
                    continue
                self.task_to_uid_queue[task].add_uid(uid)
                self.synthetic_scoring_tasks.append(
                    asyncio.create_task(
                        self.handle_task_scoring_for_uid(
                            task,
                            uid,
                            volume,
                            axon=self.uid_to_axon[uid],
                        )
                    )
                )
        bt.logging.info(f"Starting querying for {len(self.synthetic_scoring_tasks)} tasks 🔥")

    async def collect_synthetic_scoring_results(self) -> None:
        await asyncio.gather(*self.synthetic_scoring_tasks)

    async def handle_task_scoring_for_uid(
        self, task: Task, uid: axon_uid, volume: float, axon: bt.chain_data.AxonInfo
    ) -> None:
        volume_to_score = volume * self._get_percentage_of_tasks_to_score()

        uid_queue = self.task_to_uid_queue[task]

        if task not in TASK_TO_VOLUME_TO_REQUESTS_CONVERSION:
            bt.logging.warning(
                f"Task {task} not in TASK_TO_VOLUME_CONVERSION, it will not be scored. This should not happen."
            )
            return
        volume_to_requests_conversion = TASK_TO_VOLUME_TO_REQUESTS_CONVERSION[task]
        number_of_requests = max(int(volume_to_score / volume_to_requests_conversion), 1)

        uid_record = UIDRecord(
            axon_uid=uid,
            task=task,
            synthetic_requests_still_to_make=number_of_requests,
            declared_volume=volume,
            axon=axon,
            hotkey=axon.hotkey,
        )
        self.uid_records_for_tasks[task][uid] = uid_record

        delay_between_requests = (core_cst.SCORING_PERIOD_TIME * 0.98) // (number_of_requests)

        i = 0
        tasks_in_progress = []
        while uid_record.synthetic_requests_still_to_make > 0:
            # Random perturbation to make sure we dont burst
            if i == 0:
                await asyncio.sleep(delay_between_requests * random.random())
            else:
                await asyncio.sleep(delay_between_requests * (random.random() * 0.05 + 0.95))

            if i % 100 == 0 and (i > 0 or self.is_testnet):
                bt.logging.debug(
                    f"synthetic requests still to make: {uid_record.synthetic_requests_still_to_make} on iteration {i} for uid {uid_record.axon_uid} and task {task}"
                )
            if uid_record.consumed_volume >= volume_to_score:
                break

            synthetic_data = await self.synthetic_data_manager.fetch_synthetic_data_for_task(task)

            synthetic_synapse = tasks.TASKS_TO_SYNAPSE[task](**synthetic_data)
            stream = isinstance(synthetic_synapse, bt.StreamingSynapse)
            outgoing_model = getattr(base_models, synthetic_synapse.__class__.__name__ + core_cst.OUTGOING)

            if not stream:
                uid_queue.move_to_end(uid)
                tasks_in_progress.append(
                    asyncio.create_task(
                        query_utils.query_miner_no_stream(
                            uid_record, synthetic_synapse, outgoing_model, task, self.dendrite, synthetic_query=True
                        )
                    )
                )
            else:
                uid_queue.move_to_end(uid)
                generator = query_utils.query_miner_stream(
                    uid_record, synthetic_synapse, outgoing_model, task, self.dendrite, synthetic_query=True
                )
                # We need to iterate through the generator to consume it - so the request finishes
                tasks_in_progress.append(asyncio.create_task(self._consume_generator(generator)))

            # Need to make this here so its lowered regardless of the result of the above
            uid_record.synthetic_requests_still_to_make -= 1

            i += 1

        # NOTE: Do we want to do this semi regularly, to not exceed bandwidth perhaps?
        await asyncio.gather(*tasks_in_progress)
        bt.logging.info(f"Done synthetic querying for task: {task} and uid: {uid} and volume: {volume}")

    async def make_organic_query(
        self, task: Task, stream: bool, synapse: bt.Synapse, outgoing_model: BaseModel
    ) -> Union[utility_models.QueryResult, AsyncGenerator]:  # noqa: F821
        if task not in self.task_to_uid_queue:
            task_q_to_log = {k.value: len(v.uid_map) for k, v in self.task_to_uid_queue.items()}
            return JSONResponse(
                content={
                    "error": f"Task {task} not in task_to_uid_queue {task_q_to_log}. This should not happen. Type task: {type(task)}. It should be an enum"
                },
                status_code=500,
            )
        queue = self.task_to_uid_queue[task]
        latest_uid = queue.get_uid_and_move_to_back()
        if latest_uid is None:
            return JSONResponse(content={"error": f"No UIDs available for this task {task}"}, status_code=500)
        uid_record = self.uid_records_for_tasks[task][latest_uid]
        attempts = 0

        if not stream:
            while attempts < 3:
                query_result: utility_models.QueryResult = await query_utils.query_miner_no_stream(
                    uid_record,
                    synapse,
                    outgoing_model,
                    task,
                    dendrite=self.dendrite,
                    synthetic_query=False,
                )
                if query_result is None or not query_result.success:
                    attempts += 1
                else:
                    break
        else:
            while attempts < 3:
                generator = query_utils.query_miner_stream(
                    uid_record, synapse, outgoing_model, task, self.dendrite, synthetic_query=False
                )
                try:
                    first_chunk = await generator.__anext__()
                    if first_chunk is None:
                        bt.logging.info("First chunk is none")
                        return JSONResponse(
                            content={"error": f"No UIDs available for this task {task}"}, status_code=500
                        )
                    query_result = _async_chain(first_chunk, generator)
                    break
                except StopAsyncIteration:
                    attempts += 1

        if attempts == 3:
            return JSONResponse(content={"error": "Could not process request, mi apologies"}, status_code=500)
        return query_result

    @staticmethod
    def _get_percentage_of_tasks_to_score() -> float:
        """
        The function generates a random float value between 0 and 1.
        sometimes it returns 0
        sometimes it returns a random float value between 0 and 0.1.
        Otherwise, it returns a random float value between 0.4 and 0.8.

        Returns:
            float: The percentage of tasks to score.

        """
        if random.random() < 0.7:
            return 0.05
        elif random.random() < 0.9:
            return random.random() * 0.05 + 0.05
        else:
            return random.random() * 0.4 + 0.4

    @staticmethod
    async def _consume_generator(generator: AsyncGenerator) -> None:
        async for _ in generator:
            pass
