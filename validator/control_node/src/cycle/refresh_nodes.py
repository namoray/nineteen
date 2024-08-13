"""
Gets the latest nodes from the network and stores them in the database,
migrating the old nodes to history in the process
"""

import asyncio


from fiber.chain_interactions.models import Node
from validator.db.src.sql.nodes import migrate_nodes_to_history, insert_nodes
from core.logging import get_logger
from fiber.chain_interactions import fetch_nodes
from validator.control_node.src.main import Config
from validator.db.src.sql.nodes import insert_symmetric_keys_for_nodes
from fiber.validator import handshake, client
import httpx

logger = get_logger(__name__)


async def get_and_store_nodes(config: Config) -> list[Node]:
    nodes = await asyncio.to_thread(fetch_nodes.get_nodes_for_netuid, config.substrate_interface, config.netuid)
    async with await config.psql_db.connection() as connection:
        await migrate_nodes_to_history(connection)
        await insert_nodes(connection, nodes, config.network)
    logger.info(f"Stored {len(nodes)} nodes. Sleeping for {config.seconds_between_syncs} seconds.")
    return nodes


async def perform_handshakes(nodes: list[Node], config: Config) -> None:
    tasks = []
    async_client = httpx.AsyncClient()
    for node in nodes:
        server_address = client.construct_server_address(
            ip=node.ip, port=node.port, protocol=node.protocol, ip_type=node.ip_type
        )
        tasks.append(handshake.perform_handshake(async_client, server_address, config.keypair))
    keys_and_uuids: list[tuple[str, str]] = await asyncio.gather(*tasks)
    keys = [k[0] for k in keys_and_uuids]
    uuids = [k[1] for k in keys_and_uuids]
    async with await config.psql_db.connection() as connection:
        await insert_symmetric_keys_for_nodes(connection, keys, uuids)

    logger.info(f"✅ Successfully performed handshakes with {len(nodes)} nodes!")