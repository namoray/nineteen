"""
Gets the latest axons from the network and stores them in the database,
migrating the old axons to history in the process
"""

import asyncio
import os
from dataclasses import asdict, dataclass

import bittensor as bt
from dotenv import load_dotenv

from core.bittensor_overrides.chain_data import AxonInfo
from validator.db.src.database import PSQLDB
from validator.db.src import sql
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Config:
    psql_db: PSQLDB
    run_once: bool
    test_env: bool
    network: str
    netuid: int
    seconds_between_syncs: int
    metagraph: bt.metagraph
    sync: bool
    subtensor: bt.subtensor | None


def load_config() -> Config:
    load_dotenv()
    psql_db = PSQLDB()
    run_once = os.getenv("RUN_ONCE", "true").lower() == "true"
    test_env = os.getenv("ENV", "test").lower() == "test"
    network = os.getenv("NETWORK", "finney")
    netuid = int(os.getenv("NETUID", "19"))
    seconds_between_syncs = int(os.getenv("SECONDS_BETWEEN_SYNCS", "1200"))
    metagraph = bt.metagraph(netuid=netuid, network=network, lite=True, sync=False)
    sync = True
    subtensor = None  # Initialize if needed

    return Config(
        psql_db=psql_db,
        run_once=run_once,
        test_env=test_env,
        network=network,
        netuid=netuid,
        seconds_between_syncs=seconds_between_syncs,
        metagraph=metagraph,
        sync=sync,
        subtensor=subtensor,
    )


async def fetch_axon_infos_from_metagraph(config: Config) -> None:

    if config.sync:
        logger.info("Fetching axon infos from the metagraph. First, syncing...")
        await asyncio.to_thread(config.metagraph.sync, subtensor=config.subtensor, lite=True)
        logger.info("Metagraph synced, now extracting axon infos")
    else:
        logger.info("Not syncing, only extracting axon infos form metagraph object!")
        
    new_axons = [
        AxonInfo(
            **asdict(axon),
            axon_uid=uid,
            incentive=incentive,
            netuid=config.metagraph.netuid,
            network=config.metagraph.network,
            stake=stake,
        )
        for axon, uid, incentive, stake in zip(
            config.metagraph.axons,
            config.metagraph.uids,
            config.metagraph.incentive.tolist(),
            config.metagraph.S.tolist(),
        )
    ]

    logger.info(f"Synced {len(new_axons)} axons from the metagraph")
    config.metagraph.axons = new_axons


async def store_and_migrate_old_axons(config: Config) -> None:
    async with await config.psql_db.connection() as connection:
        await sql.migrate_axons_to_axon_history(connection)
        await sql.insert_axon_info(connection, config.metagraph.axons)
    logger.info(f"Stored {len(config.metagraph.axons)} axons from the metagraph")


async def get_and_store_axons(config: Config) -> None:
    if config.sync:
        await fetch_axon_infos_from_metagraph(config)

    await store_and_migrate_old_axons(config)

    logger.info(f"Stored {len(config.metagraph.axons)} axons. Sleeping for {config.seconds_between_syncs} seconds.")


async def periodically_get_and_store_axons(config: Config) -> None:
    while True:
        await get_and_store_axons(config)
        await asyncio.sleep(config.seconds_between_syncs)


async def main():
    config = load_config()

    try:
        await config.psql_db.connect()

        if config.run_once:
            logger.warning("Running once only!")
            await get_and_store_axons(config)
        else:
            await periodically_get_and_store_axons(config)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise
    finally:
        await config.psql_db.close()


if __name__ == "__main__":
    asyncio.run(main())
