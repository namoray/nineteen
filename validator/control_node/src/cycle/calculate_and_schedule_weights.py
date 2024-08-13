"""
Calculates and schedules weights every SCORING_PERIOD
"""

import asyncio
import os
from dataclasses import dataclass

from redis.asyncio import Redis
from validator.db.src.database import PSQLDB
from validator.db.src.sql.contenders import fetch_all_contenders
from validator.control_node.src.weights import calculations
from fiber.chain_interactions import weights
from core.logging import get_logger
from core import constants as ccst
from substrateinterface import SubstrateInterface, Keypair

logger = get_logger(__name__)


@dataclass(frozen=True)
class Config:
    psql_db: PSQLDB
    redis_db: Redis
    netuid: int
    substrate_interface: SubstrateInterface
    keypair: Keypair


async def load_config(substrate_interface: SubstrateInterface, keypair: Keypair) -> Config:
    psql_db = PSQLDB()
    await psql_db.connect()
    redis_db = Redis(host="redis")
    netuid = int(os.getenv("NETUID", 19))
    return Config(
        psql_db=psql_db, redis_db=redis_db, netuid=netuid, substrate_interface=substrate_interface, keypair=keypair
    )


async def _get_weights_to_set(config: Config):
    async with await config.psql_db.connection() as connection:
        contenders = await fetch_all_contenders(connection, None)

    if len(contenders) == 0:
        logger.warning("No contenders to calculate weights for!")
        return
    node_ids, node_weights = await calculations.calculate_scores_for_settings_weights(config.psql_db, contenders)
    logger.info("Weights calculated, about to set...")

    return node_ids, node_weights


async def get_and_set_weights(config: Config):
    node_ids, node_weights = await _get_weights_to_set(config)

    logger.info(f"Setting weights for {len(node_ids)} nodes...")

    success = await asyncio.to_thread(
        weights.set_node_weights(
            config.substrate_interface,
            config.keypair,
            node_ids=node_ids,
            weights=node_weights,
            netuid=config.netuid,
            version_key=ccst.VERSION_KEY,
            wait_for_inclusion=True,
            wait_for_finalization=True,
            max_attempts=3,
        )
    )

    if success:
        logger.info("Weights set successfully.")
        return

    else:
        logger.error("Failed to set weights :(")


async def main(substrate_interface: SubstrateInterface, keypair: Keypair):
    config: Config = await load_config(substrate_interface, keypair)
    try:
        while True:
            # Important to sleep first to make sure db is actually popluated
            await asyncio.sleep(
                ccst.SCORING_PERIOD_TIME + 60 * 3
            )  # wait an extra few min for everything else to finish
            await get_and_set_weights(config)
    finally:
        await config.psql_db.close()
        await config.redis_db.aclose()


if __name__ == "__main__":
    asyncio.run(main())
