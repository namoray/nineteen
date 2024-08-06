"""
Calculates period scores for participants
Converts axons to participants by querying them for their tasks. (Axon + Task = Participant)
Migrates old participants and adds the new participants to the db
"""

import asyncio
from dataclasses import dataclass
import os
from typing import List

from core.bittensor_overrides.chain_data import AxonInfo
from validator.db.src import sql
from validator.models import Participant

from dotenv import load_dotenv
from validator.db.src.database import PSQLDB
from validator.utils import query_utils as qutils
from core import tasks_config as tcfg
from core import constants as ccst
from core.tasks import Task
from redis.asyncio import Redis
from core import bittensor_overrides as bt
from models import synapses
from core.logging import get_logger
from validator.utils import generic_utils as gutils

logger = get_logger(__name__)


@dataclass
class AxonCapacity:
    hotkey: str
    miner_uid: int
    task: Task
    declared_capacity: float
    corrected_capacity: float
    capacity_to_score: float
    number_of_requests: int
    delay_between_requests: float


@dataclass
class Config:
    psql_db: PSQLDB
    redis_db: Redis
    dendrite: bt.dendrite
    validator_hotkey: str
    netuid: int


async def load_config() -> Config:
    load_dotenv()
    psql_db = PSQLDB()
    await psql_db.connect()
    redis_db = Redis(host=os.getenv("REDIS_HOST", "redis"))
    dendrite = bt.dendrite(redis_db)
    public_keypair_info = await gutils.get_public_keypair_info(redis_db)
    validator_hotkey = public_keypair_info.ss58_address
    netuid = int(os.getenv("NETUID", 19))
    return Config(psql_db, redis_db, dendrite, validator_hotkey, netuid)


def _calculate_period_score(participant: Participant) -> float:
    """
    Calculate a period score (not including quality which is scored separately)

    The closer we are to max volume used, the more forgiving we can be.
    For example, if you rate limited me loads (429), but I got most of your volume,
    then fair enough, perhaps I was querying too much

    But if I barely queried your volume, and you still rate limited me loads (429),
    then you're very naughty, you.
    """
    if participant.total_requests_made == 0 or participant.capacity == 0:
        return None

    participant.capacity = max(participant.capacity, 1)
    volume_unqueried = max(participant.capacity - participant.consumed_capacity, 0)

    percentage_of_volume_unqueried = volume_unqueried / participant.capacity
    percentage_of_429s = participant.requests_429 / participant.total_requests_made
    percentage_of_500s = participant.requests_500 / participant.total_requests_made
    percentage_of_good_requests = (
        participant.total_requests_made - participant.requests_429 - participant.requests_500
    ) / participant.total_requests_made

    # NOTE: Punish rate limit slightly less, to encourage only completing that which you can do
    rate_limit_punishment_factor = percentage_of_429s**2 * percentage_of_volume_unqueried
    server_error_punishment_factor = percentage_of_500s * percentage_of_volume_unqueried

    period_score = max(
        percentage_of_good_requests * (1 - rate_limit_punishment_factor) * (1 - server_error_punishment_factor), 0
    )

    return period_score


async def add_period_scores_to_current_participants(psql_db: PSQLDB) -> None:
    async with await psql_db.connection() as connection:
        participants = await sql.fetch_all_participants(connection, None)
        for participant in participants:
            period_score = _calculate_period_score(participant)
            participant.period_score = period_score

        await sql.update_participants_period_scores(connection, participants)


async def query_axon(dendrite: bt.dendrite, axon: AxonInfo) -> AxonCapacity:
    response = await qutils.query_individual_axon(
        synapse=synapses.Capacity(capacities=None),
        dendrite=dendrite,
        axon=axon,
        uid=axon.axon_uid,
        deserialize=True,
        log_requests_and_responses=False,
    )
    return axon.hotkey, axon.axon_uid, response[0] if response else None


async def _fetch_axon_capacities(config: Config, validator_stake_proportion: float) -> List[AxonCapacity]:
    axons = await sql.get_axons(config.psql_db, netuid=config.netuid)
    logger.info(f"Fetching capacities for {len(axons)} axons...")

    responses = await asyncio.gather(*[query_axon(config.dendrite, axon) for axon in axons[:256]])

    axon_capacities = []
    for hotkey, uid, capacities in responses:
        if capacities is None:
            continue
        for task_str, capacity in capacities.items():
            task = Task[task_str] if task_str in Task.__members__ else None
            if task is None:
                continue
            declared_capacity = float(capacity.volume)
            corrected_capacity = (
                min(max(declared_capacity, 0), tcfg.TASK_TO_CONFIG[task].max_capacity.volume)
                * validator_stake_proportion
            )
            capacity_to_score = declared_capacity * 0.1
            volume_to_requests_conversion = tcfg.TASK_TO_CONFIG[task].volume_to_requests_conversion
            number_of_requests = max(int(capacity_to_score / volume_to_requests_conversion), 1)
            delay_between_requests = (ccst.SCORING_PERIOD_TIME * 0.98) // number_of_requests

            axon_capacities.append(
                AxonCapacity(
                    hotkey=hotkey,
                    miner_uid=uid,
                    task=task,
                    declared_capacity=declared_capacity,
                    corrected_capacity=corrected_capacity,
                    capacity_to_score=capacity_to_score,
                    number_of_requests=number_of_requests,
                    delay_between_requests=delay_between_requests,
                )
            )

    logger.info(f"Got capacities from {len(axon_capacities)} axons!")
    return axon_capacities


async def store_and_migrate_old_participants(config: Config, participants: List[Participant]):
    logger.info("Calculating period scores & refreshing participants")
    async with await config.psql_db.connection() as connection:
        await sql.migrate_participants_to_participant_history(connection)
        await sql.insert_participants(connection, participants, config.validator_hotkey)


async def get_participants_from_axons(config: Config, validator_stake_proportion: float) -> List[Participant]:
    validator_stake_proportion = await get_validator_stake_proportion(
        config.psql_db, config.validator_hotkey, config.netuid
    )
    axon_capacities = await _fetch_axon_capacities(config, validator_stake_proportion)
    participants = [
        Participant(
            miner_hotkey=ac.hotkey,
            miner_uid=ac.miner_uid,
            task=ac.task,
            synthetic_requests_still_to_make=ac.number_of_requests,
            capacity=ac.corrected_capacity,
            capacity_to_score=ac.capacity_to_score,
            raw_capacity=ac.declared_capacity,
            delay_between_synthetic_requests=ac.delay_between_requests,
        )
        for ac in axon_capacities
    ]

    return participants


async def get_validator_stake_proportion(psql_db: PSQLDB, validator_hotkey: str, netuid: int) -> float:
    max_retries = 20
    retry_delay = 30
    for _ in range(max_retries):
        hotkey_to_stake = await sql.get_axon_stakes(psql_db, netuid)
        if validator_hotkey in hotkey_to_stake:
            return hotkey_to_stake[validator_hotkey] / sum(hotkey_to_stake.values())

        logger.warning(
            f"Hotkey {validator_hotkey} not found in the DB. THIS IS NORMAL at the start. Retrying in {retry_delay} seconds. Make sure the chain node is running"
        )
        await asyncio.sleep(retry_delay)

    logger.error(f"Failed to find hotkey {validator_hotkey} in stake info after {max_retries} attempts.")
    raise Exception(f"Failed to find hotkey {validator_hotkey} in stake info after {max_retries} attempts.")


async def main():
    config = await load_config()
    try:
        await add_period_scores_to_current_participants(config.psql_db)

        validator_stake_proportion = await get_validator_stake_proportion(
            config.psql_db, config.validator_hotkey, config.netuid
        )

        if validator_stake_proportion > 0:
            participants = await get_participants_from_axons(config, validator_stake_proportion)
            await store_and_migrate_old_participants(config, participants)
        else:
            logger.error("Unable to proceed without valid stake proportion.")

    except Exception as e:
        logger.error(f"Unexpected error in fetching participants: {str(e)}")
    finally:
        await config.psql_db.close()
        await config.redis_db.aclose()
        await config.dendrite.aclose_session()


if __name__ == "__main__":
    asyncio.run(main())
