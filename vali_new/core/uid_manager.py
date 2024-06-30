import asyncio
import collections
import random
from typing import AsyncGenerator, Dict, List

from core import Task, bittensor_overrides as bto
import bittensor as bt
from validation.models import UIDRecord, axon_uid
from validation.synthetic_data import synthetic_generations
from core import tasks, constants as core_cst
from validation.proxy.utils import query_utils
from models import base_models, utility_models
from validation.db.db_management import db_manager
from vali_new.core import constants as cst
from vali_new.core.utils import redis_utils
## NEEDS MOVING TO SOME CONFIG

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
        while uid_record.synthetic_requests_still_to_make > 0:
            # Random perturbation to make sure we dont burst
            if i == 0:
                await asyncio.sleep(delay_between_requests * random.random())
            else:
                await asyncio.sleep(delay_between_requests * (random.random() * 0.05 + 0.95))

            # TODO: Review if this is the best way to add tasks to some sort of queue in redis
            # Im sure there's a much better way
            synthetic_query_to_add = {"task": task, "uid": uid}
            redis_utils.add_json_to_list_in_redis(cst.SYNTHETIC_QUERIES_TO_MAKE_KEY, synthetic_query_to_add)
            if uid_record.consumed_volume >= volume_to_score:
                break

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
