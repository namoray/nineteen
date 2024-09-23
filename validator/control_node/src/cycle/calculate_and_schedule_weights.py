"""
Calculates and schedules weights every SCORING_PERIOD
"""

from dotenv import load_dotenv
import os


load_dotenv(os.getenv("ENV_FILE", ".vali.env"))

import asyncio

from validator.control_node.src.control_config import Config
from validator.control_node.src.main import load_config
from validator.db.src.sql.contenders import fetch_all_contenders
from validator.control_node.src.cycle import calculations
from fiber.chain import weights
from fiber.logging_utils import get_logger
from core import constants as ccst
from validator.db.src.sql.nodes import get_vali_node_id
from fiber.chain import fetch_nodes
from fiber.chain.models import Node

logger = get_logger(__name__)


async def _get_weights_to_set(config: Config) -> tuple[list[int], list[float]] | None:
    async with await config.psql_db.connection() as connection:
        contenders = await fetch_all_contenders(connection, None)

    if len(contenders) == 0:
        logger.warning("No contenders to calculate weights for!")
        return None
    else:
        logger.info(f"Found {len(contenders)} contenders to get weights for")
    node_ids, node_weights = await calculations.calculate_scores_for_settings_weights(config.psql_db, contenders)

    return node_ids, node_weights


async def get_and_set_weights(config: Config) -> None:
    validator_node_id = await get_vali_node_id(config.psql_db, config.netuid)
    if validator_node_id is None:
        raise ValueError("Validator node id not found")
    result = await _get_weights_to_set(config)
    if result is None:
        logger.info("No weights to set. Skipping weight setting.")
        return
    node_ids, node_weights = result
    logger.info("Weights calculated, about to set...")
    logger.info(f"Node ids: {node_ids}")
    logger.info(f"Node weights: {node_weights}")

    if len(node_ids) == 0:
        logger.info("No nodes to set weights for. Skipping weight setting.")
        return
    logger.info(f"Setting weights for {len(node_ids)} nodes...")

    success = await asyncio.to_thread(
        weights.set_node_weights,
        substrate=config.substrate,
        keypair=config.keypair,
        node_ids=node_ids,
        node_weights=node_weights,
        netuid=config.netuid,
        version_key=ccst.VERSION_KEY,
        validator_node_id=int(validator_node_id),
        wait_for_inclusion=True,
        wait_for_finalization=True,
        max_attempts=3,
    )

    if success:
        logger.info("Weights set successfully.")
    else:
        logger.error("Failed to set weights :(")


async def main():
    logger.info("Starting weight calculation...")
    config = load_config()
    logger.debug(f"Config: {config}")
    await config.psql_db.connect()

    success = await get_and_set_weights(config)
    if not success:
        logger.error("Failed to set weights using db values :(")

    # To prevent validators getting deregistered - but up to them to use this and they should prioritise the values they have above
    logger.warning(
        "\n\n!!!! Setting weights using the metagraph only since we have no data on the miners in the db. Please cancel if you do not want to do this !!! \n\n"
    )
    await asyncio.sleep(10)
    nodes: list[Node] = fetch_nodes.get_nodes_for_netuid(config.substrate, config.netuid)
    node_ids = [node.node_id for node in nodes]
    node_weights = [node.incentive for node in nodes]
    validator_node_id = await get_vali_node_id(config.psql_db, config.netuid)
    if validator_node_id is None:
        raise ValueError("Validator node id not found")

    await asyncio.to_thread(
        weights.set_node_weights,
        substrate=config.substrate,
        keypair=config.keypair,
        node_ids=node_ids,
        node_weights=node_weights,
        netuid=config.netuid,
        version_key=ccst.VERSION_KEY,
        validator_node_id=int(validator_node_id),
        wait_for_inclusion=True,
        wait_for_finalization=True,
        max_attempts=3,
    )


if __name__ == "__main__":
    asyncio.run(main())
