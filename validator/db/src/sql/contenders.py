from typing import Any

from asyncpg import Connection
from fiber.logging_utils import get_logger

from validator.db.src.database import PSQLDB
from validator.models import Contender, PeriodScore, calculate_period_score
from validator.utils.database import database_constants as dcst
from validator.utils.generic import generic_constants as gcst

logger = get_logger(__name__)


async def insert_contenders(
    connection: Connection, contenders: list[Contender], validator_hotkey: str
) -> None:
    logger.debug(f"Inserting {len(contenders)} contender records")

    await connection.executemany(
        f"""
        INSERT INTO {dcst.CONTENDERS_TABLE} (
            {dcst.CONTENDER_ID},
            {dcst.NODE_HOTKEY},
            {dcst.NODE_ID},
            {dcst.NETUID},
            {dcst.TASK},
            {dcst.VALIDATOR_HOTKEY},
            {dcst.CAPACITY},
            {dcst.RAW_CAPACITY},
            {dcst.CAPACITY_TO_SCORE},
            {dcst.CONSUMED_CAPACITY},
            {dcst.TOTAL_REQUESTS_MADE},
            {dcst.REQUESTS_429},
            {dcst.REQUESTS_500},
            {dcst.CREATED_AT},
            {dcst.UPDATED_AT}
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW(), NOW())
        """,
        [
            (
                contender.id,
                contender.node_hotkey,
                contender.node_id,
                contender.netuid,
                contender.task,
                validator_hotkey,
                contender.capacity,
                contender.raw_capacity,
                contender.capacity_to_score,
                contender.consumed_capacity,
                contender.total_requests_made,
                contender.requests_429,
                contender.requests_500,
            )
            for contender in contenders
        ],
    )


async def migrate_contenders_to_contender_history(connection: Connection) -> None:
    await connection.execute(
        f"""
        INSERT INTO {dcst.CONTENDERS_HISTORY_TABLE} (
            {dcst.CONTENDER_ID},
            {dcst.NODE_HOTKEY},
            {dcst.NODE_ID},
            {dcst.NETUID},
            {dcst.TASK},
            {dcst.VALIDATOR_HOTKEY},
            {dcst.CAPACITY},
            {dcst.RAW_CAPACITY},
            {dcst.CAPACITY_TO_SCORE},
            {dcst.CONSUMED_CAPACITY},
            {dcst.TOTAL_REQUESTS_MADE},
            {dcst.REQUESTS_429},
            {dcst.REQUESTS_500},
            {dcst.PERIOD_SCORE},
            {dcst.CREATED_AT},
            {dcst.UPDATED_AT}
        )
        SELECT
            {dcst.CONTENDER_ID},
            {dcst.NODE_HOTKEY},
            {dcst.NODE_ID},
            {dcst.NETUID},
            {dcst.TASK},
            {dcst.VALIDATOR_HOTKEY},
            {dcst.CAPACITY},
            {dcst.RAW_CAPACITY},
            {dcst.CAPACITY_TO_SCORE},
            {dcst.CONSUMED_CAPACITY},
            {dcst.TOTAL_REQUESTS_MADE},
            {dcst.REQUESTS_429},
            {dcst.REQUESTS_500},
            {dcst.PERIOD_SCORE},
            {dcst.CREATED_AT},
            {dcst.UPDATED_AT}
        FROM {dcst.CONTENDERS_TABLE}
        """
    )

    await connection.execute(f"DELETE FROM {dcst.CONTENDERS_TABLE}")


async def get_contenders_for_task(
    connection: Connection, task: str, query_type: str = gcst.ORGANIC, top_x: int = 5
) -> list[Contender]:
    """
    Fetch a list of contenders for a given task, ordered based on the query type.

    For organic queries:
        - Prioritize contenders with the highest PERIOD_SCORE (best performance).
    For synthetic queries:
        - Prioritize contenders with the least TOTAL_REQUESTS_MADE (need more assessment).

    Parameters:
        connection (Connection): The database connection.
        task (str): The task name.
        query_type (str): 'organic' or 'synthetic'.
        top_x (int): The number of contenders to fetch.

    Returns:
        List[Contender]: A list of Contender objects.
    """
    # Determine the ORDER BY clause based on the query type
    order_by = (
        # For synthetic queries, we want to assess miners with fewer requests made
        f"ORDER BY c.{dcst.TOTAL_REQUESTS_MADE} ASC"
        if query_type == gcst.SYNTHETIC
        # For organic queries, we want the best performers
        else f"ORDER BY c.{dcst.PERIOD_SCORE} DESC NULLS LAST"
    )

    # Initial query to fetch contenders based on the determined order
    rows: list[dict[str, Any]] = await connection.fetch(
        f"""
        SELECT
            c.{dcst.CONTENDER_ID},
            c.{dcst.NODE_HOTKEY},
            c.{dcst.NODE_ID},
            c.{dcst.TASK},
            c.{dcst.RAW_CAPACITY},
            c.{dcst.CAPACITY_TO_SCORE},
            c.{dcst.CONSUMED_CAPACITY},
            c.{dcst.TOTAL_REQUESTS_MADE},
            c.{dcst.REQUESTS_429},
            c.{dcst.REQUESTS_500},
            c.{dcst.CAPACITY},
            c.{dcst.PERIOD_SCORE},
            c.{dcst.NETUID}
        FROM {dcst.CONTENDERS_TABLE} c
        JOIN {dcst.NODES_TABLE} n
            ON c.{dcst.NODE_ID} = n.{dcst.NODE_ID}
            AND c.{dcst.NETUID} = n.{dcst.NETUID}
        WHERE c.{dcst.TASK} = $1
            AND c.{dcst.CAPACITY} > 0  -- Ensure miner has capacity
            AND n.{dcst.SYMMETRIC_KEY_UUID} IS NOT NULL  -- Ensure necessary keys are available
        {order_by}
        LIMIT $2
        """,
        task,
        top_x,
    )

    # Check if we have enough contenders
    if not rows or len(rows) < top_x:
        # Prepare a list of already selected contender IDs to avoid duplicates
        selected_contender_ids = [str(row[dcst.CONTENDER_ID]) for row in rows]
        not_in_clause = (
            f"AND c.{dcst.CONTENDER_ID} NOT IN ({','.join(selected_contender_ids)})"
            if selected_contender_ids
            else ""
        )

        # Determine the secondary ORDER BY clause
        secondary_order_by = (
            # For organic queries, include miners without scores if needed
            f"ORDER BY c.{dcst.PERIOD_SCORE} IS NULL ASC, c.{dcst.PERIOD_SCORE} DESC"
            if query_type == gcst.ORGANIC
            # For synthetic queries, continue to prioritize least assessed miners
            else f"ORDER BY c.{dcst.TOTAL_REQUESTS_MADE} ASC"
        )

        # Secondary query to fetch additional contenders
        secondary_rows: list[dict[str, Any]] = await connection.fetch(
            f"""
            SELECT
                c.{dcst.CONTENDER_ID},
                c.{dcst.NODE_HOTKEY},
                c.{dcst.NODE_ID},
                c.{dcst.TASK},
                c.{dcst.RAW_CAPACITY},
                c.{dcst.CAPACITY_TO_SCORE},
                c.{dcst.CONSUMED_CAPACITY},
                c.{dcst.TOTAL_REQUESTS_MADE},
                c.{dcst.REQUESTS_429},
                c.{dcst.REQUESTS_500},
                c.{dcst.CAPACITY},
                c.{dcst.PERIOD_SCORE},
                c.{dcst.NETUID}
            FROM {dcst.CONTENDERS_TABLE} c
            JOIN {dcst.NODES_TABLE} n
                ON c.{dcst.NODE_ID} = n.{dcst.NODE_ID}
                AND c.{dcst.NETUID} = n.{dcst.NETUID}
            WHERE c.{dcst.TASK} = $1
                AND c.{dcst.CAPACITY} > 0
                AND n.{dcst.SYMMETRIC_KEY_UUID} IS NOT NULL
                {not_in_clause}  -- Exclude already selected contenders
            {secondary_order_by}
            LIMIT $2
            """,
            task,
            top_x - len(rows) if rows else top_x,  # Only add the needed additional rows
        )

        # Combine initial and secondary results
        rows.extend(secondary_rows)

    # Convert the result rows into Contender objects
    return [Contender(**row) for row in rows]


async def update_contender_capacities(
    psql_db: PSQLDB, contender: Contender, capacitity_consumed: float
) -> None:
    async with await psql_db.connection() as connection:
        await connection.execute(
            f"""
            UPDATE {dcst.CONTENDERS_TABLE}
            SET {dcst.CONSUMED_CAPACITY} = {dcst.CONSUMED_CAPACITY} + $1, 
                {dcst.TOTAL_REQUESTS_MADE} = {dcst.TOTAL_REQUESTS_MADE} + 1
            WHERE {dcst.CONTENDER_ID} = $2
            """,
            capacitity_consumed,
            contender.id,
        )


async def update_contender_429_count(psql_db: PSQLDB, contender: Contender) -> None:
    async with await psql_db.connection() as connection:
        await connection.execute(
            f"""
            UPDATE {dcst.CONTENDERS_TABLE}
            SET {dcst.REQUESTS_429} = {dcst.REQUESTS_429} + 1,
                {dcst.TOTAL_REQUESTS_MADE} = {dcst.TOTAL_REQUESTS_MADE} + 1
            WHERE {dcst.CONTENDER_ID} = $1
            """,
            contender.id,
        )


async def update_contender_500_count(psql_db: PSQLDB, contender: Contender) -> None:
    async with await psql_db.connection() as connection:
        await connection.execute(
            f"""
            UPDATE {dcst.CONTENDERS_TABLE}
            SET {dcst.REQUESTS_500} = {dcst.REQUESTS_500} + 1,
                {dcst.TOTAL_REQUESTS_MADE} = {dcst.TOTAL_REQUESTS_MADE} + 1
            WHERE {dcst.CONTENDER_ID} = $1
            """,
            contender.id,
        )


async def fetch_contender(
    connection: Connection, contender_id: str
) -> Contender | None:
    row = await connection.fetchrow(
        f"""
        SELECT 
            {dcst.CONTENDER_ID}, {dcst.NODE_HOTKEY}, {dcst.NODE_ID},{dcst.TASK},
            {dcst.CAPACITY}, {dcst.RAW_CAPACITY}, {dcst.CAPACITY_TO_SCORE},
             {dcst.CONSUMED_CAPACITY}, {dcst.TOTAL_REQUESTS_MADE}, {dcst.REQUESTS_429}, {dcst.REQUESTS_500}, 
            {dcst.PERIOD_SCORE}
        FROM {dcst.CONTENDERS_TABLE} 
        WHERE {dcst.CONTENDER_ID} = $1
        """,
        contender_id,
    )
    if not row:
        return None
    return Contender(**row)


async def fetch_all_contenders(
    connection: Connection, netuid: int | None = None
) -> list[Contender]:
    base_query = f"""
        SELECT 
            {dcst.CONTENDER_ID}, {dcst.NODE_HOTKEY}, {dcst.NODE_ID}, {dcst.NETUID}, {dcst.TASK}, 
            {dcst.RAW_CAPACITY}, {dcst.CAPACITY_TO_SCORE}, {dcst.CONSUMED_CAPACITY}, 
            {dcst.TOTAL_REQUESTS_MADE}, {dcst.REQUESTS_429}, {dcst.REQUESTS_500}, 
            {dcst.CAPACITY}, {dcst.PERIOD_SCORE}
        FROM {dcst.CONTENDERS_TABLE}
        """
    if netuid is None:
        rows = await connection.fetch(base_query)
    else:
        rows = await connection.fetch(base_query + f" WHERE {dcst.NETUID} = $1", netuid)
    return [Contender(**row) for row in rows]


async def fetch_hotkey_scores_for_task(
    connection: Connection, task: str, node_hotkey: str
) -> list[PeriodScore]:
    rows = await connection.fetch(
        f"""
        SELECT
            {dcst.NODE_HOTKEY} as hotkey,
            {dcst.TASK},
            {dcst.PERIOD_SCORE},
            {dcst.CONSUMED_CAPACITY},
            {dcst.CREATED_AT}
        FROM {dcst.CONTENDERS_HISTORY_TABLE}
        WHERE {dcst.TASK} = $1
        AND {dcst.NODE_HOTKEY} = $2
        ORDER BY {dcst.CREATED_AT} DESC
        """,
        task,
        node_hotkey,
    )
    return [PeriodScore(**row) for row in rows]


async def update_contenders_period_scores(connection: Connection, netuid: int) -> None:
    rows = await connection.fetch(
        f"""
        SELECT 
            {dcst.CONTENDER_ID},
            {dcst.TOTAL_REQUESTS_MADE},
            {dcst.CAPACITY},
            {dcst.CONSUMED_CAPACITY},
            {dcst.REQUESTS_429},
            {dcst.REQUESTS_500}
        FROM {dcst.CONTENDERS_TABLE}
        WHERE {dcst.NETUID} = $1
    """,
        netuid,
    )

    updates = []
    for row in rows:
        score = calculate_period_score(
            float(row[dcst.TOTAL_REQUESTS_MADE]),
            float(row[dcst.CAPACITY]),
            float(row[dcst.CONSUMED_CAPACITY]),
            float(row[dcst.REQUESTS_429]),
            float(row[dcst.REQUESTS_500]),
        )
        if score is not None:
            updates.append((score, row[dcst.CONTENDER_ID]))

    logger.info(f"Updating {len(updates)} contenders with new period scores")

    await connection.executemany(
        f"""
        UPDATE {dcst.CONTENDERS_TABLE}
        SET {dcst.PERIOD_SCORE} = $1,
            {dcst.UPDATED_AT} = NOW() AT TIME ZONE 'UTC'
        WHERE {dcst.CONTENDER_ID} = $2
    """,
        updates,
    )
    logger.info(f"Updated {len(updates)} contenders with new period scores")


async def get_and_decrement_synthetic_request_count(
    connection: Connection, contender_id: str
) -> int | None:
    """
    Asynchronously retrieves and decrements the synthetic request count for a given contender, setting it to 0 if
    it the consumed capacity is greater than the announced capacity.
    """

    result = await connection.fetchrow(
        f"""
        UPDATE {dcst.CONTENDERS_TABLE}
        SET {dcst.SYNTHETIC_REQUESTS_STILL_TO_MAKE} = 
            CASE 
                WHEN {dcst.CONSUMED_CAPACITY} > {dcst.CAPACITY} THEN 0
                ELSE GREATEST({dcst.SYNTHETIC_REQUESTS_STILL_TO_MAKE} - 1, 0)
            END
        WHERE {dcst.CONTENDER_ID} = $1
        RETURNING {dcst.SYNTHETIC_REQUESTS_STILL_TO_MAKE}
        """,
        contender_id,
    )

    if result:
        return result[dcst.SYNTHETIC_REQUESTS_STILL_TO_MAKE]
    else:
        return None
