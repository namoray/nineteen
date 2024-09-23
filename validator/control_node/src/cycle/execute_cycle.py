"""
A cycle consists of
- Refreshing metagraph to get nodes (if not refreshed for X time in the case of restarts)
- Handshaking with the nodes
- Gathering the contenders from the nodes by querying for capacities
- Deciding what % of each contender should be queried
- Scheduling synthetics according the the amount of volume I need to query
- Getting the contender_scores from the 429's, 500's and successful queries
- Calculating weights when the scoring period is expired
- Setting the weights on the nodes async while starting the next cycle
"""

import asyncio
from validator.control_node.src.control_config import Config
from validator.control_node.src.cycle import (
    calculate_and_schedule_weights,
    refresh_nodes,
    refresh_contenders,
    schedule_synthetic_queries,
    # calculate_and_schedule_weights,
)
from core import constants as ccst
from validator.db.src.sql.nodes import (
    get_nodes,
)
from core.log import get_logger

from validator.models import Contender


logger = get_logger(__name__)


async def get_nodes_and_contenders(config: Config) -> list[Contender] | None:
    logger.info("Starting cycle...")
    if config.refresh_nodes:
        logger.info("First refreshing metagraph and storing the nodes")
        nodes = await refresh_nodes.get_and_store_nodes(config)
    else:
        nodes = await get_nodes(config.psql_db, config.netuid)

    logger.info("Got nodes! Performing handshakes now...")

    nodes = await refresh_nodes.perform_handshakes(nodes, config)

    logger.info("Got handshakes! Getting the contenders from the nodes...")

    contenders = await refresh_contenders.get_and_store_contenders(config, nodes)

    logger.info(f"Got all contenders! {len(contenders)} contenders will be queried...")

    return contenders


async def schedule_synthetics(config: Config) -> None:
    logger.info(f"Scheduling synthetics; this will take {ccst.SCORING_PERIOD_TIME // 60} minutes ish...")

    await schedule_synthetic_queries.schedule_synthetics_until_done(config)


async def main(config: Config) -> None:
    time_to_sleep_if_no_contenders = 20
    contenders = await get_nodes_and_contenders(config)
    if contenders is None or len(contenders) == 0:
        logger.info(
            f"No contenders to query, skipping synthetic scheduling and sleeping for {time_to_sleep_if_no_contenders} seconds to wait."
        )
        await asyncio.sleep(time_to_sleep_if_no_contenders)  # Sleep for 5 minutes to wait for contenders to become available
        tasks = []
    else:
        tasks = [schedule_synthetics(config)]
    while True:
        await asyncio.gather(*tasks)
        contenders = await get_nodes_and_contenders(config)
        if contenders is None or len(contenders) == 0:
            logger.info(
                f"No contenders to query, skipping synthetic scheduling and sleeping for {time_to_sleep_if_no_contenders} seconds to wait."
            )
            await asyncio.sleep(time_to_sleep_if_no_contenders)  # Sleep for 5 minutes to wait for contenders to become available
            tasks = []
        else:
            tasks = [calculate_and_schedule_weights.get_and_set_weights(config), schedule_synthetics(config)]
