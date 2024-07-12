import asyncio
import random
import threading
from typing import List

import bittensor as bt
from models import utility_models

from redis.asyncio import Redis
from vali_new.models import Participant
from vali_new.utils import redis_utils as rutils, query_utils as qutils
from vali_new.utils import redis_constants as cst
from core import constants as ccst
from collections import defaultdict
from typing import Dict, Tuple
from typing import Optional
from core import tasks, utils as cutils

from core import Task
from core import bittensor_overrides as bto
from models import base_models, synapses


# Replace with some global threading lock?
threading_lock = threading.Lock()


async def _sync_metagraph(redis_db: Redis, metagraph: bt.metagraph, subtensor: bt.subtensor) -> None:
    bt.logging.info("Resyncing the metagraph!")
    await asyncio.to_thread(metagraph.sync, subtensor=subtensor, lite=True)

    bt.logging.info("Got the capacities, now storing the info....")
    _, axon_indexes_tensor = metagraph.incentive.sort(descending=True)

    with threading_lock:
        uids: List[int] = metagraph.uids.tolist()
        axon_indexes = axon_indexes_tensor.tolist()
        hotkeys: List[str] = metagraph.hotkeys  # noqa: F841
        axons = metagraph.axons

        for i in axon_indexes:
            uid, hotkey, axon = uids[i], hotkeys[i], axons[i]
            hotkey_info = utility_models.HotkeyInfo(
                uid=uid,
                axon=axon,
                hotkey=hotkey,
            )
            # TODO: Is this the best way to store the info?
            await rutils.save_json_to_redis(redis_db, cst.HOTKEY_INFO_KEY + hotkey, hotkey_info.dict())

    return hotkeys


async def _fetch_available_capacities_for_each_axon(
    redis_db: Redis, hotkeys: List[str], dendrite: bto.dendrite
) -> None:
    hotkey_to_query_task = {}

    for hotkey in hotkeys:
        # NOTE: Doesn't seem the most efficient to use redis here... lol
        hotkey_info = utility_models.HotkeyInfo(
            **(await rutils.json_load_from_redis(redis_db, cst.HOTKEY_INFO_KEY + hotkey))
        )
        task = asyncio.create_task(
            qutils.query_individual_axon(
                synapse=synapses.Capacity(),
                dendrite=dendrite,
                axon=hotkey_info.axon,
                uid=hotkey_info.uid,
                deserialize=True,
                log_requests_and_responses=False,
            )
        )

        hotkey_to_query_task[hotkey] = task

    responses_and_response_times: List[
        Tuple[Optional[Dict[Task, base_models.VolumeForTask]], float]
    ] = await asyncio.gather(*hotkey_to_query_task.values())

    all_capacities = [i[0] for i in responses_and_response_times]

    bt.logging.info(f"Got capacities from {len([i for i in all_capacities if i is not None])} axons!")
    with threading_lock:
        capacities_for_tasks = defaultdict(lambda: {})
        for hotkey, capacities in zip(hotkeys, all_capacities):
            if capacities is None:
                continue

            allowed_tasks = set([task for task in Task])
            for task, volume in capacities.items():
                # This is to stop people claiming tasks that don't exist
                if task not in allowed_tasks:
                    continue
                if hotkey not in capacities_for_tasks[task]:
                    capacities_for_tasks[task][hotkey] = float(volume.volume)
        return capacities_for_tasks


def _correct_capacities(capacities_for_tasks: Dict[Task, Dict[str, float]]):
    return capacities_for_tasks


async def _store_capacities_in_redis(redis_db: Redis, capacities_for_tasks: Dict[Task, Dict[str, float]]):
    await rutils.save_json_to_redis(redis_db, cst.CAPACITIES_KEY, capacities_for_tasks)


async def _store_all_participants_in_redis(
    redis_db: Redis,
    capacities_for_tasks: Dict[Task, Dict[str, float]],
):
    for task in Task:
        for hotkey, declared_volume in capacities_for_tasks.get(task, {}).items():
            volume_to_score, number_of_requests_to_make, delay_between_requests = calculate_synthetic_query_parameters(
                task, declared_volume
            )
            await store_participant(
                redis_db,
                task,
                hotkey,
                declared_volume,
                volume_to_score,
                number_of_requests_to_make,
                delay_between_requests,
            )


def _get_percentage_of_tasks_to_score():
    return 1


def calculate_synthetic_query_parameters(task: Task, declared_volume: float):
    assert (
        task in tasks.TASK_TO_VOLUME_TO_REQUESTS_CONVERSION
    ), f"Task {task} not in TASK_TO_VOLUME_CONVERSION, it will not be scored. This should not happen."

    volume_to_score = declared_volume * _get_percentage_of_tasks_to_score()
    volume_to_requests_conversion = tasks.TASK_TO_VOLUME_TO_REQUESTS_CONVERSION[task]
    number_of_requests_to_make = max(int(volume_to_score / volume_to_requests_conversion), 1)
    delay_between_requests = (ccst.SCORING_PERIOD_TIME * 0.98) // (number_of_requests_to_make)

    return volume_to_score, number_of_requests_to_make, delay_between_requests


async def store_participant(
    redis_db: Redis,
    task: Task,
    hotkey: str,
    declared_volume: float,
    volume_to_score,
    number_of_requests_to_make,
    delay_between_synthetic_requests,
):
    participant = Participant(
        hotkey=hotkey,
        task=task,
        synthetic_requests_still_to_make=number_of_requests_to_make,
        declared_volume=declared_volume,
        volume_to_score=volume_to_score,
        delay_between_synthetic_requests=delay_between_synthetic_requests,
    )
    # How should i best do this, with redisJSON perhaps?

    await rutils.save_json_to_redis(redis_db, key=participant.id, json_to_save=participant.model_dump())
    await rutils.add_to_set_redis(redis_db, cst.PARTICIPANT_IDS_KEY, participant.id)
    return participant.id


async def get_and_store_participant_info(redis_db: Redis, metagraph: bt.metagraph, subtensor: bt.subtensor):
    hotkeys = await _sync_metagraph(redis_db, metagraph, subtensor)
    capacities_for_tasks = await _fetch_available_capacities_for_each_axon(hotkeys)
    corrected_capacities = _correct_capacities(capacities_for_tasks)
    await _store_capacities_in_redis(corrected_capacities)
    await _store_all_participants_in_redis(redis_db, capacities_for_tasks)


## Testing utils
async def patched_get_and_store_participant_info(redis_db: Redis, number_of_participants: int = 10) -> None:
    participants_dict = {}
    for i in range(number_of_participants):
        hotkey = "hotkey" + str(random.randint(1, 10_000))
        vol = (random.random() *4000 + 1000)
        participants_dict[hotkey] = vol

    capacities_for_tasks = {Task.chat_llama_3:participants_dict }
    await _store_capacities_in_redis(redis_db, capacities_for_tasks)
    await _store_all_participants_in_redis(redis_db, capacities_for_tasks)


async def main():
    redis_db = Redis()
    config = cutils.prepare_config_and_logging()
    subtensor = bt.subtensor(config=config)
    metagraph = subtensor.metagraph(netuid=config.netuid, lite=True)
    await get_and_store_participant_info(redis_db, metagraph, subtensor)


if __name__ == "__main__":
    asyncio.run(main())
