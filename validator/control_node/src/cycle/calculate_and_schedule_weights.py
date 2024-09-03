"""
Calculates and schedules weights every SCORING_PERIOD
"""

import asyncio

from validator.control_node.src.control_config import Config
from validator.db.src.sql.contenders import fetch_all_contenders
from validator.control_node.src.cycle import calculations
from fiber.chain_interactions import weights
from core.logging import get_logger
from core import constants as ccst
from validator.db.src.sql.nodes import get_vali_node_id

logger = get_logger(__name__)


async def _get_weights_to_set(config: Config) -> tuple[list[int], list[float]] | None:
    async with await config.psql_db.connection() as connection:
        contenders = await fetch_all_contenders(connection, None)

    if len(contenders) == 0:
        logger.warning("No contenders to calculate weights for!")
        return None
    else:
        logger.debug(f"Found {len(contenders)} contenders")
    node_ids, node_weights = await calculations.calculate_scores_for_settings_weights(config.psql_db, contenders)

    return node_ids, node_weights


async def get_and_set_weights(config: Config) -> None:
    result = await _get_weights_to_set(config)
    if result is None:
        logger.info("No weights to set. Skipping weight setting.")
        return
    node_ids, node_weights = result
    logger.info("Weights calculated, about to set...")

    validator_node_id = await get_vali_node_id(config.psql_db, config.netuid)

    logger.info(f"Setting weights for {len(node_ids)} nodes...")

    success = await asyncio.to_thread(
        weights.set_node_weights,
        substrate_interface=config.substrate_interface,
        keypair=config.keypair,
        node_ids=node_ids,
        node_weights=node_weights,
        netuid=config.netuid,
        version_key=ccst.VERSION_KEY,
        validator_node_id=validator_node_id,
        wait_for_inclusion=True,
        wait_for_finalization=True,
        max_attempts=3,
    )

    if success:
        logger.info("Weights set successfully.")
    else:
        logger.error("Failed to set weights :(")
