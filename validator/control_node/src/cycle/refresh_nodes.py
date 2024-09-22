"""
Gets the latest nodes from the network and stores them in the database,
migrating the old nodes to history in the process
"""

import asyncio


from fiber.chain.models import Node
from validator.db.src.sql.nodes import get_nodes, migrate_nodes_to_history, insert_nodes, get_last_updated_time_for_nodes
from core.log import get_logger
from fiber.chain import fetch_nodes
from validator.control_node.src.control_config import Config
from validator.db.src.sql.nodes import insert_symmetric_keys_for_nodes, update_our_vali_node_in_db
from fiber.validator import handshake, client
import httpx
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

logger = get_logger(__name__)


async def get_and_store_nodes(config: Config) -> list[Node]:
    async with await config.psql_db.connection() as connection:
        if await is_recent_update(connection, config.netuid):
            return await get_nodes(config.psql_db, config.netuid)

    nodes = await fetch_nodes_from_substrate(config)

    await store_nodes(config, nodes)
    await update_our_validator_node(config)

    logger.info(f"Stored {len(nodes)} nodes.")
    return nodes


async def is_recent_update(connection, netuid: int) -> bool:
    last_updated_time = await get_last_updated_time_for_nodes(connection, netuid)
    if last_updated_time is not None and datetime.now() - last_updated_time < timedelta(minutes=30):
        logger.info(
            f"Last update for nodes table was at {last_updated_time}, which is less than 30 minutes ago - skipping refresh"
        )
        return True
    return False


async def fetch_nodes_from_substrate(config: Config) -> list[Node]:
    # NOTE: Will this cause issues if this method closes the conenction
    # on substrate interface, but we use the same substrate interface object elsewhere?
    return await asyncio.to_thread(fetch_nodes.get_nodes_for_netuid, config.substrate, config.netuid)


async def store_nodes(config: Config, nodes: list[Node]):
    async with await config.psql_db.connection() as connection:
        await migrate_nodes_to_history(connection)
        await insert_nodes(connection, nodes, config.subtensor_network)


async def update_our_validator_node(config: Config):
    async with await config.psql_db.connection() as connection:
        await update_our_vali_node_in_db(connection, config.keypair.ss58_address, config.netuid)


async def _handshake(config: Config, node: Node, async_client: httpx.AsyncClient) -> Node:
    node_copy = node.model_copy()
    server_address = client.construct_server_address(
        node=node,
        replace_with_docker_localhost=config.replace_with_docker_localhost,
        replace_with_localhost=config.replace_with_localhost,
    )

    try:
        symmetric_key, symmetric_key_uid = await handshake.perform_handshake(
            async_client, server_address, config.keypair, node.hotkey
        )
    except (httpx.HTTPStatusError, httpx.RequestError, httpx.ConnectError, Exception) as e:
        # logger.warning(f"Failed to connect to {server_address}: {e}")
        if hasattr(e, "response"):
            logger.debug(f"response content: {e.response.text}")  # type: ignore
        return node_copy

    fernet = Fernet(symmetric_key)
    node_copy.fernet = fernet
    node_copy.symmetric_key_uuid = symmetric_key_uid
    return node_copy


async def perform_handshakes(nodes: list[Node], config: Config) -> list[Node]:
    tasks = []
    for node in nodes:
        if node.fernet is None or node.symmetric_key_uuid is None:
            tasks.append(_handshake(config, node, config.httpx_client))

    nodes = await asyncio.gather(*tasks)

    async with await config.psql_db.connection() as connection:
        await insert_symmetric_keys_for_nodes(connection, nodes)

    logger.info(f"✅ performed handshakes with {len(nodes)} nodes!")
    return nodes
