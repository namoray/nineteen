"""
Gets the latest nodes from the network and stores them in the database,
migrating the old nodes to history in the process
"""

import asyncio


from fiber.chain_interactions.models import Node
from validator.db.src.sql.nodes import (
    migrate_nodes_to_history,
    insert_nodes,
    get_last_updated_time_for_nodes,
    get_nodes,
)
from core.logging import get_logger
from fiber.chain_interactions import fetch_nodes
from validator.control_node.src.main import Config
from validator.db.src.sql.nodes import insert_symmetric_keys_for_nodes
from fiber.validator import handshake, client
import httpx
from datetime import datetime, timedelta

logger = get_logger(__name__)


async def _handshake(node: Node, async_client: httpx.AsyncClient, config: Config) -> tuple[str, str] | None:
    server_address = client.construct_server_address(
        ip=node.ip, port=node.port, protocol=node.protocol, ip_type=node.ip_type
    )
    if config.debug:
        return await handshake.perform_handshake(async_client, server_address, config.keypair)
    else:
        try:
            return await handshake.perform_handshake(async_client, server_address, config.keypair)
        except (httpx.HTTPStatusError, httpx.RequestError, httpx.ConnectError):
            return None


async def get_and_store_nodes(config: Config) -> list[Node]:
    async with await config.psql_db.connection() as connection:
        if await is_recent_update(connection, config.netuid):
            return await get_nodes(config.psql_db, config.netuid)

    nodes = await fetch_nodes_from_substrate(config)
    await store_nodes(config, nodes)
    
    logger.info(f"Stored {len(nodes)} nodes. Sleeping for {config.seconds_between_syncs} seconds.")
    return nodes

async def is_recent_update(connection, netuid: int) -> bool:
    last_updated_time = await get_last_updated_time_for_nodes(connection, netuid)
    if last_updated_time and datetime.now() - last_updated_time < timedelta(minutes=30):
        logger.info(
            f"Last update for nodes table was at {last_updated_time}, which is less than 30 minutes ago - skipping refresh"
        )
        return True
    return False

async def fetch_nodes_from_substrate(config: Config) -> list[Node]:
    return await asyncio.to_thread(
        fetch_nodes.get_nodes_for_netuid,
        config.substrate_interface,
        config.netuid
    )

async def store_nodes(config: Config, nodes: list[Node]):
    async with await config.psql_db.connection() as connection:
        await migrate_nodes_to_history(connection)
        await insert_nodes(connection, nodes, config.subtensor_network)


async def perform_handshakes(nodes: list[Node], config: Config) -> None:
    tasks = []
    async_client = httpx.AsyncClient()
    for node in nodes:
        # TODO: Don't do it for nodes which already have a symmetric key?
        tasks.append(_handshake(node, async_client, config))

    key_infos: list[tuple[str, str]] = await asyncio.gather(*tasks)
    good_nodes = []
    keys = []
    uuids = []
    for node, key_info in zip(nodes, key_infos):
        if node is not None and key_info is not None:
            good_nodes.append(node)
            keys.append(key_info[0])
            uuids.append(key_info[1])

    async with await config.psql_db.connection() as connection:
        await insert_symmetric_keys_for_nodes(connection, nodes, keys, uuids)

    logger.info(f"✅ Successfully performed handshakes with {len(nodes)} nodes!")
