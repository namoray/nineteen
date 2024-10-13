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
from typing import List

from fiber.logging_utils import get_logger

from core import constants as ccst
from core.task_config import get_public_task_configs
from validator.control_node.src.control_config import Config
from validator.control_node.src.cycle import refresh_contenders
from validator.control_node.src.cycle import refresh_nodes
from validator.control_node.src.cycle.schedule_synthetic_queries import schedule_synthetics_until_done
from validator.db.src.sql.nodes import get_nodes
from validator.models import Contender
from validator.utils.post.nineteen import DataTypeToPost
from validator.utils.post.nineteen import ValidatorInfoPostBody
from validator.utils.post.nineteen import post_to_nineteen_ai


logger = get_logger(__name__)


async def _post_vali_stats(config: Config):
    public_configs = get_public_task_configs()
    await post_to_nineteen_ai(
        data_to_post=ValidatorInfoPostBody(
            validator_hotkey=config.keypair.ss58_address,
            task_configs=public_configs,
            versions=str(ccst.VERSION_KEY),
        ).model_dump(mode="json"),
        keypair=config.keypair,
        data_type_to_post=DataTypeToPost.VALIDATOR_INFO,
    )


async def get_nodes_and_contenders(config: Config) -> List[Contender] | None:
    logger.info("Starting cycle...")
    if config.refresh_nodes:
        logger.info("Refreshing metagraph and storing the nodes.")
        nodes = await refresh_nodes.get_and_store_nodes(config)
    else:
        nodes = await get_nodes(config.psql_db, config.netuid)

    await _post_vali_stats(config)

    logger.info("Nodes refreshed! Performing handshakes now...")

    nodes = await refresh_nodes.perform_handshakes(nodes, config)

    logger.info("Handshakes completed! Fetching contenders from the nodes...")

    contenders = await refresh_contenders.get_and_store_contenders(config, nodes)

    logger.info(f"Contenders fetched! Total contenders: {len(contenders)}.")

    return contenders


async def main(config: Config) -> None:
    time_to_sleep_if_no_contenders = 20
    contenders = await get_nodes_and_contenders(config)

    await warmup_function(config=config)

    if not contenders:
        logger.info(
            f"No contenders available. Skipping synthetic scheduling and sleeping for {time_to_sleep_if_no_contenders} seconds."
        )
        await asyncio.sleep(time_to_sleep_if_no_contenders)
        tasks = []
    else:
        tasks = [schedule_synthetics_until_done(config)]

    while True:
        await asyncio.gather(*tasks)
        contenders = await get_nodes_and_contenders(config)
        if not contenders:
            logger.info(
                f"No contenders available. Skipping synthetic scheduling and sleeping for {time_to_sleep_if_no_contenders} seconds."
            )
            await asyncio.sleep(time_to_sleep_if_no_contenders)
            tasks = []
        else:
            tasks = [schedule_synthetics_until_done(config)]
