"""
Calculates period scores for contenders
Converts axons to contenders by querying them for their tasks. (Axon + Task = Contender)
Migrates old contenders and adds the new contenders to the db
"""

import asyncio
from typing import List


from validator.db.src import sql
from validator.models import Contender
from fiber.chain_interactions.models import Node
from validator.db.src.database import PSQLDB
from core import tasks_config as tcfg
from core import constants as ccst
from core.tasks import Task
from validator.control_node.src.main import Config
from dataclasses import dataclass
from core.logging import get_logger

from fiber.validator import client

logger = get_logger(__name__)


# TODO: Should we just have this extend a node? or encapsulate it
@dataclass
class NodeCapacity:
    hotkey: str
    node_id: int
    task: Task
    netuid: int
    declared_capacity: float
    corrected_capacity: float
    capacity_to_score: float
    number_of_requests: int
    delay_between_requests: float
    validator_hotkey: str


def _calculate_period_score(contender: Contender) -> float:
    """
    Calculate a period score (not including quality which is scored separately)

    The closer we are to max volume used, the more forgiving we can be.
    For example, if you rate limited me loads (429), but I got most of your volume,
    then fair enough, perhaps I was querying too much

    But if I barely queried your volume, and you still rate limited me loads (429),
    then you're very naughty, you.
    """
    # TODO: revisit whether `500's` makes sense
    if contender.total_requests_made == 0 or contender.capacity == 0:
        return None

    contender.capacity = max(contender.capacity, 1)
    volume_unqueried = max(contender.capacity - contender.consumed_capacity, 0)

    percentage_of_volume_unqueried = volume_unqueried / contender.capacity
    percentage_of_429s = contender.requests_429 / contender.total_requests_made
    percentage_of_500s = contender.requests_500 / contender.total_requests_made
    percentage_of_good_requests = (
        contender.total_requests_made - contender.requests_429 - contender.requests_500
    ) / contender.total_requests_made

    # NOTE: Punish rate limit slightly less, to encourage miners to not exceed their bandwidth
    rate_limit_punishment_factor = percentage_of_429s**2 * percentage_of_volume_unqueried
    server_error_punishment_factor = percentage_of_500s * percentage_of_volume_unqueried

    period_score = max(
        percentage_of_good_requests * (1 - rate_limit_punishment_factor) * (1 - server_error_punishment_factor), 0
    )

    return period_score


async def add_period_scores_to_current_contenders(psql_db: PSQLDB) -> None:
    async with await psql_db.connection() as connection:
        contenders = await sql.fetch_all_contenders(connection, None)
        for contender in contenders:
            period_score = _calculate_period_score(contender)
            contender.period_score = period_score

        await sql.update_contenders_period_scores(connection, contenders)


async def _fetch_node_capacity(config: Config, node: Node) -> NodeCapacity:
    logger.info(f"Posting to endpoint /capacity on {node}...")
    await client.make_non_streamed_get(
        httpx_client=config.httpx_client,
        server_address=client.construct_server_address(node),
        validator_ss58_address=config.keypair.ss58_address,
        fernet=node.fernet,
        symmetric_key_uuid=node.symmetric_key_uuid,
        endpoint="/capacity",
        timeout=3,
    )


async def _fetch_node_capacities(config: Config, nodes: list[Node]) -> List[NodeCapacity]:
    capacity_tasks = []
    for node in nodes:
        capacity_tasks.append(_fetch_node_capacity(config, node))

    capacities = await asyncio.gather(*capacity_tasks)
    return capacities

    return
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
                NodeCapacity(
                    hotkey=hotkey,
                    node_id=uid,
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


async def store_and_migrate_old_contenders(config: Config, contenders: List[Contender]):
    logger.info("Calculating period scores & refreshing contenders")
    async with await config.psql_db.connection() as connection:
        await sql.migrate_contenders_to_contender_history(connection)
        await sql.insert_contenders(connection, contenders, config.validator_hotkey)


async def get_contenders_from_nodes(config: Config, nodes: list[Node]) -> List[Contender]:
    axon_capacities = await _fetch_node_capacities(config, nodes)
    return
    validator_stake_proportion = await get_validator_stake_proportion(
        config.psql_db, config.validator_hotkey, config.netuid
    )
    contenders = [
        Contender(
            miner_hotkey=ac.hotkey,
            miner_uid=ac.node_id,
            task=ac.task,
            synthetic_requests_still_to_make=ac.number_of_requests,
            capacity=ac.corrected_capacity,
            capacity_to_score=ac.capacity_to_score,
            raw_capacity=ac.declared_capacity,
            delay_between_synthetic_requests=ac.delay_between_requests,
        )
        for ac in axon_capacities
    ]

    return contenders


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
        await add_period_scores_to_current_contenders(config.psql_db)

        validator_stake_proportion = await get_validator_stake_proportion(
            config.psql_db, config.validator_hotkey, config.netuid
        )

        if validator_stake_proportion > 0:
            contenders = await get_contenders_from_nodes(config, validator_stake_proportion)
            await store_and_migrate_old_contenders(config, contenders)
        else:
            logger.error("Unable to proceed without valid stake proportion.")

    except Exception as e:
        logger.error(f"Unexpected error in fetching contenders: {str(e)}")
    finally:
        await config.psql_db.close()
        await config.redis_db.aclose()
        await config.dendrite.aclose_session()


if __name__ == "__main__":
    asyncio.run(main())
