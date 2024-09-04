"""
Calculates period scores for contenders
Converts NODEs to contenders by querying them for their tasks. (NODE + Task = Contender)
Migrates old contenders and adds the new contenders to the db
"""

import asyncio
from typing import List


from validator.db.src.sql.contenders import migrate_contenders_to_contender_history, insert_contenders, update_contenders_period_scores
from validator.models import Contender
from fiber.chain_interactions.models import Node
from core import tasks_config as tcfg
from core.tasks import Task
from validator.control_node.src.control_config import Config
from core.logging import get_logger

from fiber.validator import client

logger = get_logger(__name__)


def _get_validator_stake_proportion(nodes: list[Node], hotkey_ss58_address: str) -> float:
    valid_nodes = [node for node in nodes if node is not None and node.stake is not None]
    sum_stake = sum(node.stake for node in valid_nodes)
    target_node = next((node for node in valid_nodes if node.hotkey == hotkey_ss58_address), None)
    if target_node is not None:
        return target_node.stake / sum_stake

    logger.error(f"Unable to find validator {hotkey_ss58_address} in nodes.")
    raise ValueError(f"Unable to find validator {hotkey_ss58_address} in nodes.")


def _get_capacity_to_score(capacity: float, capacity_to_score_multiplier: float) -> float:
    """TODO: Finish"""
    return capacity * capacity_to_score_multiplier


async def _store_and_migrate_old_contenders(config: Config, new_contenders: List[Contender]):
    logger.info("Calculating period scores & refreshing contenders")
    async with await config.psql_db.connection() as connection:
        await update_contenders_period_scores(connection, config.netuid)
        await migrate_contenders_to_contender_history(connection)
        await insert_contenders(connection, new_contenders, config.keypair.ss58_address)


async def _fetch_node_capacity(config: Config, node: Node) -> dict[str, float] | None:
    server_address = client.construct_server_address(
        node=node,
        replace_with_docker_localhost=config.replace_with_docker_localhost,
        replace_with_localhost=config.replace_with_localhost,
    )
    response = await client.make_non_streamed_get(
        httpx_client=config.httpx_client,
        server_address=server_address,
        validator_ss58_address=config.keypair.ss58_address,
        symmetric_key_uuid=node.symmetric_key_uuid,
        endpoint="/capacity",
        timeout=3,
    )

    if response.status_code != 200:
        logger.warning(f"Failed to fetch capacity from node {node.node_id}")
        return None

    return response.json()


async def _fetch_node_capacities(config: Config, nodes: list[Node]) -> list[dict[str, float] | None]:
    async def _fetch_or_none(node: Node):
        if node.fernet is None or node.symmetric_key_uuid is None:
            return None
        return await _fetch_node_capacity(config, node)

    capacity_tasks = [_fetch_or_none(node) for node in nodes]
    capacities = await asyncio.gather(*capacity_tasks)
    return capacities


async def _get_contenders_from_nodes(config: Config, nodes: list[Node]) -> List[Contender]:
    validator_stake_proportion = _get_validator_stake_proportion(nodes, config.keypair.ss58_address)
    raw_capacities = await _fetch_node_capacities(config, nodes)
    logger.debug(f"Got capacities: {raw_capacities}")
    logger.info(f"Got capacities for {len([i for i in raw_capacities if i is not None])} nodes")

    contenders = []
    for node, raw_node_capacities in zip(nodes, raw_capacities):
        if raw_node_capacities is None:
            continue
        logger.debug(f"Node: {node}\n capacities: {raw_node_capacities}")
        node_hotkey = node.hotkey
        node_id = node.node_id
        netuid = node.netuid
        for task, declared_capacity in raw_node_capacities.items():
            logger.info(f"Task: {task}\n Capacity: {declared_capacity}")
            if task not in Task._value2member_map_:
                logger.debug(f"Task {task} is not a valid task")
                continue

            task_config = tcfg.get_enabled_task_config(Task(task))
            if task_config is None:
                continue
            capacity = min(max(declared_capacity, 0), task_config.max_capacity) * validator_stake_proportion
            capacity_to_score = _get_capacity_to_score(capacity, config.capacity_to_score_multiplier)

            contenders.append(
                Contender(
                    node_hotkey=node_hotkey,
                    node_id=node_id,
                    netuid=netuid,
                    task=task,
                    raw_capacity=declared_capacity,
                    capacity=capacity,
                    capacity_to_score=capacity_to_score,
                )
            )

    logger.info(f"Got {len(contenders)} contenders to score")
    return contenders


async def get_and_store_contenders(config: Config, nodes: list[Node]) -> None:
    logger.info(f"Got {len(nodes)} nodes")
    contenders = await _get_contenders_from_nodes(config, nodes)
    await _store_and_migrate_old_contenders(config, contenders)
    return contenders
