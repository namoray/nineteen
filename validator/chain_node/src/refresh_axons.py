"""
Gets the latest nodes from the network and stores them in the database,
migrating the old nodes to history in the process
"""

import asyncio
import os
from dataclasses import dataclass

from asyncpg import Connection
from dotenv import load_dotenv

from validator.db.src.database import PSQLDB
from validator.db.src.sql.nodes import migrate_nodes_to_history, insert_nodes
from core.logging import get_logger
from substrateinterface import SubstrateInterface, Keypair
from fiber.chain_interactions import interface
from fiber.chain_interactions import chain_utils, fetch_nodes
from fiber.chain_interactions.models import Node

logger = get_logger(__name__)


@dataclass
class Config:
    psql_db: PSQLDB
    run_once: bool
    test_env: bool
    network: str
    netuid: int
    seconds_between_syncs: int
    substrate_interface: SubstrateInterface
    sync: bool
    keypair: Keypair


def load_config() -> Config:
    load_dotenv()
    psql_db = PSQLDB()
    run_once = os.getenv("RUN_ONCE", "true").lower() == "true"
    test_env = os.getenv("ENV", "test").lower() == "test"
    chain_network = os.getenv("CHAIN_NETWORK")
    chain_address = os.getenv("CHAIN_ADDRESS")
    wallet_name = os.getenv("WALLET_NAME", "default")
    hotkey_name = os.getenv("HOTKEY_NAME", "default")
    netuid = int(os.getenv("NETUID", "19"))
    seconds_between_syncs = int(os.getenv("SECONDS_BETWEEN_SYNCS", "1200"))
    sync = True
    substrate_interface = interface.get_substrate_interface(chain_network=chain_network, chain_address=chain_address)
    keypair = chain_utils.load_hotkey_keypair(wallet_name=wallet_name, hotkey_name=hotkey_name)

    return Config(
        psql_db=psql_db,
        run_once=run_once,
        test_env=test_env,
        network=chain_network,
        netuid=netuid,
        seconds_between_syncs=seconds_between_syncs,
        sync=sync,
        substrate_interface=substrate_interface,
        keypair=keypair,
    )


async def fetch_nodes_from_metagraph(config: Config) -> list[Node]:
    nodes = await asyncio.to_thread(fetch_nodes.get_nodes_for_netuid(config.substrate_interface, config.netuid))
    return nodes


async def store_and_migrate_old_nodes(connection: Connection, nodes: list[Node]) -> None:
    logger.debug("Storing and migrating old nodes...")

    await migrate_nodes_to_history(connection)
    await insert_nodes(connection, nodes)
    logger.info(f"Stored {len(nodes)} nodes from the metagraph")


async def get_and_store_nodes(config: Config) -> None:
    if config.sync:
        nodes = await fetch_nodes_from_metagraph(config)

    async with await config.psql_db.connection() as connection:
        await store_and_migrate_old_nodes(config, connection)

    logger.info(f"Stored {len(nodes)} nodes. Sleeping for {config.seconds_between_syncs} seconds.")


async def periodically_get_and_store_nodes(config: Config) -> None:
    while True:
        await get_and_store_nodes(config)
        await asyncio.sleep(config.seconds_between_syncs)


async def main():
    config = load_config()

    try:
        await config.psql_db.connect()

        if config.run_once:
            logger.warning("Running once only!")
            await get_and_store_nodes(config)
        else:
            await periodically_get_and_store_nodes(config)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise
    finally:
        await config.psql_db.close()


if __name__ == "__main__":
    asyncio.run(main())
