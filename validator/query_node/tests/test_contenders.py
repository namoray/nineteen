"""
Simple script which tests contender ranking algorithm.
"""

import asyncio
import time

import asyncpg
from asyncpg import Connection
from fiber.logging_utils import get_logger
from fiber.networking.models import NodeWithFernet as Node

from validator.db.src.database import PSQLDB
from validator.db.src.sql.contenders import (
    get_contenders_for_task, insert_contenders,
    migrate_contenders_to_contender_history, update_contenders_period_scores)
from validator.db.src.sql.nodes import insert_nodes, migrate_nodes_to_history
from validator.models import Contender
from validator.utils.database import database_constants as dcst

logger = get_logger(__name__)


def get_contender(node_id: int, task: str) -> Contender:
    cont = Contender(
        node_hotkey=str(node_id),
        node_id=node_id,
        netuid=1,
        task=task,
        raw_capacity=50,
        capacity=50,
        capacity_to_score=50,
        consumed_capacity=50,
        total_requests_made=100,
        requests_429=0,
        requests_500=0,
        period_score=None,
        final_rank=None,
    )
    return cont


def get_node(node_id: int) -> Node:
    return Node(
        hotkey=str(node_id),
        coldkey=str(node_id),
        node_id=node_id,
        incentive=1,
        netuid=1,
        stake=0,
        trust=1,
        vtrust=1,
        last_updated=0,
        port=8091,
        ip_type=4,
        protocol=4,
        symmetric_key_uuid="1234",
        ip="0.0.0.0",
    )


async def populate_nodes(connection: Connection, epochs: int = 5):
    for _ in range(epochs):
        await migrate_nodes_to_history(connection)
        await insert_nodes(connection, [get_node(i) for i in range(1, 11)], "1")
        await connection.execute(  # set explciitly to None in insert_nodes methods, need this to be set in order for contender to be eligible
            f"""
            UPDATE {dcst.NODES_TABLE}
            SET {dcst.SYMMETRIC_KEY} = 1234, {dcst.SYMMETRIC_KEY_UUID} = 1234
            """,
        )


async def populate_tasks(connection: Connection):
    try:
        await connection.execute(
            """
    INSERT INTO public.task_similarity
    (left_task, right_task, similarity)
    VALUES('CHAT_LLAMA_3_1_800B', 'CHAT_LLAMA_3_2_3B', 0.5);
                                 
                        """
        )
    except asyncpg.exceptions.UniqueViolationError as uve:
        logger.debug("Task similarities already populated")


async def populate_contenders(
    connection: Connection, validator_hotkey: str, epochs: int = 5
):
    for epoch in range(epochs):
        await update_contenders_period_scores(connection, 1)
        await migrate_contenders_to_contender_history(connection)
        for ind, task in enumerate(
            ["CHAT_LLAMA_3_2_3B", "CHAT_LLAMA_3_1_8B", "CHAT_LLAMA_3_1_70B"]
        ):
            await insert_contenders(
                connection,
                [get_contender(i, task) for i in range(1, epoch + 2)],
                validator_hotkey,
            )
        if epoch == epochs - 1:  # wake up babe, new llama dropped
            await insert_contenders(
                connection,
                [get_contender(i, "CHAT_LLAMA_3_1_800B") for i in range(1, epoch + 2)],
                validator_hotkey,
            )
        time.sleep(1)


async def populate_database(
    connection: Connection, validator_hotkey: str, epochs: int = 5
):
    await populate_nodes(connection, epochs)
    await populate_tasks(connection)
    await populate_contenders(connection, validator_hotkey, epochs)
    logger.debug("Database has been populated")


async def clear_database(connection: Connection):
    await connection.execute(
        """
    delete from nodes;
    delete from nodes_history;
    delete from contenders;
    delete from contenders_history; 
    delete from task_similarity;
"""
    )
    logger.debug("Database has been cleared")


async def run_test():
    psql_db = PSQLDB()
    await psql_db.connect()
    async with await psql_db.connection() as connection:
        await populate_database(connection, "4321")
        for contender in await get_contenders_for_task(
            connection, "CHAT_LLAMA_3_2_3B", top_x=5, dropoff_interval_seconds=1
        ):
            logger.debug(
                f"Contender with id {contender.id} has a rank of {contender.final_rank}"
            )
            logger.debug(
                f"Total metric was {100 - contender.final_rank}" # type: ignore
            )
        for contender in await get_contenders_for_task(
            connection, "CHAT_LLAMA_3_1_800B", top_x=5, dropoff_interval_seconds=1
        ):
            logger.debug(
                f"Contender with id {contender.id} has a rank of {contender.final_rank}"
            )
            logger.debug(
                f"Total metric was {100 - contender.final_rank}" # type: ignore
            )
        await clear_database(connection)


if __name__ == "__main__":
    asyncio.run(run_test())
