import asyncio
import threading

import bittensor as bt
from core.bittensor_overrides.chain_data import AxonInfo
from models import config_models

from redis.asyncio import Redis
from validator.db.database import PSQLDB
from validator.models import Participant
from validator.utils import redis_utils as rutils, query_utils as qutils
from validator.utils import redis_constants as cst
from core import constants as ccst
from collections import defaultdict
from core import tasks
from config import configuration
from core import Task

from core import bittensor_overrides as bto
from models import base_models, synapses
from validator.db import sql
from core.logging import get_logger


logger = get_logger(__name__)

# Replace with some global threading lock?
threading_lock = threading.Lock()


async def _sync_metagraph(metagraph: bt.metagraph, subtensor: bt.subtensor) -> None:
    logger.info("Resyncing the metagraph!")
    await asyncio.to_thread(metagraph.sync, subtensor=subtensor, lite=True)


async def store_metagraph_info(postgresql_db: PSQLDB, metagraph: bt.metagraph) -> list[str]:
    axons = metagraph.axons

    for axon in axons:
        logger.debug(f"Storing axon info: {axon}")
        await sql.insert_axon_info(postgresql_db, axon)
        # TODO: Is this the best way to store the info?
        # NO; I think this should really go into a sql table


async def _fetch_available_capacities_for_each_axon(psql_db: PSQLDB, dendrite: bto.dendrite) -> None:
    hotkey_to_query_task = {}

    axons = await sql.get_axons(psql_db)

    for axon in axons:
        # NOTE: Doesn't seem the most efficient to use redis here... lol
        task = asyncio.create_task(
            qutils.query_individual_axon(
                synapse=synapses.Capacity(),
                dendrite=dendrite,
                axon=axon,
                uid=axon.axon_uid,
                deserialize=True,
                log_requests_and_responses=False,
            )
        )

        hotkey_to_query_task[axon.hotkey] = task

    responses_and_response_times: list[
        tuple[dict[Task, base_models.VolumeForTask] | None, float]
    ] = await asyncio.gather(*hotkey_to_query_task.values())

    all_capacities = [i[0] for i in responses_and_response_times]

    bt.logging.info(f"Got capacities from {len([i for i in all_capacities if i is not None])} axons!")
    with threading_lock:
        capacities_for_tasks = defaultdict(lambda: {})
        for hotkey, capacities in zip([axon.hotkey for axon in axons], all_capacities):
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


def _correct_capacities(capacities_for_tasks: dict[Task, dict[str, float]]):
    return capacities_for_tasks


# TODO: replace with psql
# async def _store_capacities_in_redis(redis_db: Redis, capacities_for_tasks: dict[Task, dict[str, float]]):
#     await rutils.save_json_to_redis(redis_db, cst.CAPACITIES_KEY, capacities_for_tasks)


# TODO: Replace with psql
async def _store_all_participants_in_redis(
    redis_db: Redis,
    capacities_for_tasks: dict[Task, dict[str, float]],
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
                synthetic_requests_still_to_make=number_of_requests_to_make,
                delay_between_synthetic_requests=delay_between_requests,
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


# TODO: replace with psql
async def store_participant(
    redis_db: Redis,
    task: Task,
    hotkey: str,
    declared_volume: float,
    volume_to_score: float,
    synthetic_requests_still_to_make: int,
    delay_between_synthetic_requests: float,
):
    participant = Participant(
        hotkey=hotkey,
        task=task,
        synthetic_requests_still_to_make=synthetic_requests_still_to_make,
        declared_volume=declared_volume,
        volume_to_score=volume_to_score,
        delay_between_synthetic_requests=delay_between_synthetic_requests,
    )
    # How should i best do this, with redisJSON perhaps?

    await rutils.save_json_to_redis(redis_db, key=participant.id, json_to_save=participant.model_dump())
    await rutils.add_to_set_redis(redis_db, cst.PARTICIPANT_IDS_KEY, participant.id)
    return participant.id


async def get_and_store_participant_info(
    psql_db: PSQLDB, metagraph: bt.metagraph, subtensor: bt.subtensor, dendrite: bto.dendrite, sync: bool = True
):
    if sync:
        await _sync_metagraph(metagraph, subtensor)

    await store_metagraph_info(psql_db, metagraph)
    # capacities_for_tasks = await _fetch_available_capacities_for_each_axon(psql_db, dendrite)
    # corrected_capacities = _correct_capacities(capacities_for_tasks)
    # await _store_capacities_in_redis(corrected_capacities)
    # await _store_all_participants_in_redis(psql_db, capacities_for_tasks)


## Testing utils
async def patched_get_and_store_participant_info(
    psql_db: PSQLDB,
    metagraph: bt.metagraph,
    subtensor: bt.subtensor,
    dendrite: bto.dendrite,
    sync: bool = True,
    number_of_participants: int = 10,
):
    if sync:
        await _sync_metagraph(metagraph, subtensor)

    await store_metagraph_info(psql_db, metagraph)
    # participants_dict = {}
    # for i in range(number_of_participants):
    #     hotkey = "hotkey" + str(random.randint(1, 10_000))
    #     vol = random.random() * 4000 + 1000
    #     participants_dict[hotkey] = vol

    # capacities_for_tasks = {Task.chat_llama_3: participants_dict}
    # await _store_capacities_in_redis(redis_db, capacities_for_tasks)
    # await _store_all_participants_in_redis(redis_db, capacities_for_tasks)


async def main():
    # Remember to export ENV=test
    redis_db = Redis()
    psql_db = PSQLDB()
    await psql_db.connect()
    validator_config = config_models.ValidatorConfig()
    config = configuration.prepare_validator_config_and_logging(validator_config)
    # subtensor = bt.subtensor(config=config)
    subtensor = None
    metagraph = bt.metagraph(netuid=config.netuid, lite=True, sync=False)

    # Don't need to set this, as it's a property derived from the axons
    # metagraph.hotkeys = ["test-hotkey1", "test-hotkey2"]
    metagraph.axons = [
        AxonInfo(
            version=1, ip="127.0.0.1", port=1, ip_type=4, hotkey="test-hotkey1", coldkey="test-coldkey1", axon_uid=1
        ),
        AxonInfo(
            version=2, ip="127.0.0.1", port=2, ip_type=4, hotkey="test-hotkey2", coldkey="test-coldkey2", axon_uid=2
        ),
    ]
    dendrite = None
    await patched_get_and_store_participant_info(psql_db, metagraph, subtensor, dendrite, sync=False)


if __name__ == "__main__":
    asyncio.run(main())
