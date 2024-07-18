import asyncio
import threading

import bittensor as bt
import numpy as np
from core.bittensor_overrides.chain_data import AxonInfo
from models import config_models
from dataclasses import asdict
from validator.db.database import PSQLDB
from validator.models import Participant
from validator.utils import query_utils as qutils
from core import task_config as tcfg
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
    new_axons = []
    incentives = metagraph.incentive.tolist()
    logger.debug(f"Incentives: {incentives}")
    for (
        axon,
        uid,
        incentive,
    ) in zip(metagraph.axons, metagraph.uids, incentives):
        new_axon_info = AxonInfo(**asdict(axon), axon_uid=uid, incentive=incentive)
        logger.debug(f"New axon info: {new_axon_info}")
        new_axons.append(new_axon_info)

    metagraph.axons = new_axons


async def store_metagraph_info(psql_db: PSQLDB, metagraph: bt.metagraph) -> list[str]:
    axons = metagraph.axons

    async with await psql_db.connection() as connection:
        await sql.migrate_axons_to_axon_history(connection)
        await sql.insert_axon_info(connection, axons)


async def _fetch_available_capacities_for_each_axon(psql_db: PSQLDB, dendrite: bto.dendrite) -> None:
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

    bt.logging.info(f"Got capacities from {len([i for i in all_capacities if i is not None])} axons!")
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
    max_capacity = tcfg.TASK_TO_MAX_CAPACITY[task]

    announced_capacity = min(max(capacity, 0), max_capacity.capacity)
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
            capacity_to_score, number_of_requests_to_make, delay_between_requests = (
                calculate_synthetic_query_parameters(task, declared_capacity)
            )
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
    metagraph: bt.metagraph,
    subtensor: bt.subtensor,
    dendrite: bto.dendrite,
    validator_hotkey: str,
    sync: bool = True,
    number_of_participants: int = 10,
):
    if sync:
        await _sync_metagraph(metagraph, subtensor)

    await store_metagraph_info(psql_db, metagraph)
    capacities_for_tasks = await _fetch_available_capacities_for_each_axon(psql_db, dendrite)

    validator_stake_proportion = metagraph.S[metagraph.hotkeys.index(validator_hotkey)] / metagraph.S.sum()
    await _store_all_participants_in_db(psql_db, capacities_for_tasks, validator_hotkey, validator_stake_proportion)


def set_for_dummy_run(metagraph: bt.metagraph) -> None:
    # Don't need to set this, as it's a property derived from the axons
    # metagraph.hotkeys = ["test-hotkey1", "test-hotkey2"]

    metagraph.axons = [
        # Vali
        AxonInfo(
            version=1,
            ip="127.0.0.1",
            port=1,
            ip_type=4,
            hotkey="test-vali",
            coldkey="test-vali-ck",
            axon_uid=0,
            incentive=0,
        ),
        # Miners
        AxonInfo(
            version=1,
            ip="127.0.0.1",
            port=1,
            ip_type=4,
            hotkey="test-hotkey1",
            coldkey="test-coldkey1",
            axon_uid=1,
            incentive=0.004,
        ),
        AxonInfo(
            version=2,
            ip="127.0.0.1",
            port=2,
            ip_type=4,
            hotkey="test-hotkey2",
            coldkey="test-coldkey2",
            axon_uid=2,
            incentive=0.005,
        ),
    ]
    metagraph.total_stake = np.array([50, 30, 20])
    dendrite = None
    sync = False
    return dendrite, sync


async def main():
    # Remember to export ENV=test
    psql_db = PSQLDB()
    await psql_db.connect()
    validator_config = config_models.ValidatorConfig()
    config = configuration.prepare_validator_config_and_logging(validator_config)
    subtensor = None
    metagraph = bt.metagraph(netuid=config.netuid, lite=True, sync=False)

    # Use below to control dummy data
    RUN_WITH_DUMMY = True
    if RUN_WITH_DUMMY:
        dendrite, sync = set_for_dummy_run(metagraph)
    else:
        wallet = bt.wallet(name=config.wallet_name, hotkey=config.hotkey_name)
        dendrite = bto.dendrite(wallet=wallet)

    await get_and_store_participant_info(
        psql_db, metagraph, subtensor, dendrite, validator_hotkey="test-vali", sync=sync
    )


if __name__ == "__main__":
    asyncio.run(main())
