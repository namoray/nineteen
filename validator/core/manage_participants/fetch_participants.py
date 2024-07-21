import asyncio
import threading

from validator.db.database import PSQLDB
from validator.models import Participant
from validator.utils import query_utils as qutils
from core import tasks_config as tcfg
from core import constants as ccst
from collections import defaultdict
from core import tasks
from core import Task

from core import bittensor_overrides as bt
from models import base_models, synapses
from validator.db import sql
from core.logging import get_logger


logger = get_logger(__name__)

# Replace with some global threading lock?
threading_lock = threading.Lock()


def _get_percentage_of_tasks_to_score():
    return 1


async def _get_validator_stake_proportion(
    psql_db: PSQLDB,
    validator_hotkey: str,
):
    hotkey_to_stake = await sql.get_axon_stakes(psql_db)

    return hotkey_to_stake[validator_hotkey] / sum(hotkey_to_stake.values())


async def _fetch_available_capacities_for_each_axon(psql_db: PSQLDB, dendrite: bt.dendrite) -> None:
    hotkey_to_query_task = {}

    axons = await sql.get_axons(psql_db)

    for axon in axons:
        task = asyncio.create_task(
            qutils.query_individual_axon(
                synapse=synapses.Capacity(capacities=None),
                dendrite=dendrite,
                axon=axon,
                uid=axon.axon_uid,
                deserialize=True,
                log_requests_and_responses=False,
            )
        )

        hotkey_to_query_task[axon.hotkey] = task

    responses_and_response_times: list[
        tuple[dict[Task, base_models.CapacityForTask] | None, float]
    ] = await asyncio.gather(*hotkey_to_query_task.values())

    all_capacities = [i[0] for i in responses_and_response_times]

    logger.info(f"Got capacities from {len([i for i in all_capacities if i is not None])} axons!")
    with threading_lock:
        capacities_for_tasks = defaultdict(lambda: {})
        for hotkey, capacities in zip([axon.hotkey for axon in axons], all_capacities):
            if capacities is None:
                continue

            allowed_tasks = set([task for task in Task])
            for task, capacity in capacities.items():
                # This is to stop people claiming tasks that don't exist
                if task not in allowed_tasks:
                    continue
                if hotkey not in capacities_for_tasks[task]:
                    capacities_for_tasks[task][hotkey] = float(capacity.capacity)
    return capacities_for_tasks


def _correct_capacity(task: Task, capacity: float, validator_stake_proportion: float) -> float:
    max_capacity = tcfg.TASK_TO_CONFIG[task].max_capacity.capacity

    announced_capacity = min(max(capacity, 0), max_capacity)
    return announced_capacity * validator_stake_proportion


# TODO: Replace with psql
async def _store_all_participants_in_db(
    psql_db: PSQLDB,
    capacities_for_tasks: dict[Task, dict[str, float]],
    validator_hotkey: str,
    validator_stake_proportion: float,
):
    participants = []
    for task in Task:
        for hotkey, declared_capacity in capacities_for_tasks.get(task, {}).items():
            (
                capacity_to_score,
                number_of_requests_to_make,
                delay_between_requests,
            ) = calculate_synthetic_query_parameters(task, declared_capacity)
            corrected_capacity = _correct_capacity(task, declared_capacity, validator_stake_proportion)
            participant = Participant(
                miner_hotkey=hotkey,
                task=task,
                synthetic_requests_still_to_make=number_of_requests_to_make,
                capacity=corrected_capacity,
                capacity_to_score=capacity_to_score,
                raw_capacity=declared_capacity,
                delay_between_synthetic_requests=delay_between_requests,
            )
            participants.append(participant)

    await store_participants(psql_db, participants, validator_hotkey)


def calculate_synthetic_query_parameters(task: Task, declared_volume: float):
    assert (
        task in tasks.TASK_TO_VOLUME_TO_REQUESTS_CONVERSION
    ), f"Task {task} not in TASK_TO_VOLUME_CONVERSION, it will not be scored. This should not happen."

    volume_to_score = declared_volume * _get_percentage_of_tasks_to_score()
    volume_to_requests_conversion = tasks.TASK_TO_VOLUME_TO_REQUESTS_CONVERSION[task]
    number_of_requests_to_make = max(int(volume_to_score / volume_to_requests_conversion), 1)
    delay_between_requests = (ccst.SCORING_PERIOD_TIME * 0.98) // (number_of_requests_to_make)

    return volume_to_score, number_of_requests_to_make, delay_between_requests


async def store_participants(
    psql_db: PSQLDB,
    participants: list[Participant],
    validator_hotkey: str,
):
    async with await psql_db.connection() as connection:
        await sql.migrate_participants_to_participant_history(connection)
        await sql.insert_participants(connection, participants, validator_hotkey)


## Testing utils
async def get_and_store_participant_info(
    psql_db: PSQLDB,
    dendrite: bt.dendrite,
    validator_hotkey: str,
):
    capacities_for_tasks = await _fetch_available_capacities_for_each_axon(psql_db, dendrite)

    validator_stake_proportion = await _get_validator_stake_proportion(psql_db, validator_hotkey)

    await _store_all_participants_in_db(psql_db, capacities_for_tasks, validator_hotkey, validator_stake_proportion)


async def main(run_with_dummy: bool = True):
    # Remember to export ENV=test
    psql_db = PSQLDB()
    await psql_db.connect()
    dendrite = bt.dendrite()

    await get_and_store_participant_info(psql_db, dendrite, validator_hotkey="test-vali")


if __name__ == "__main__":
    asyncio.run(main())
