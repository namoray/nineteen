from datetime import datetime, timezone
from typing import Any

from asyncpg import Connection
from fiber.logging_utils import get_logger

from core import constants as ccst
from validator.db.src.database import PSQLDB
from validator.models import Contender, PeriodScore, calculate_period_score
from validator.utils.database import database_constants as dcst
from validator.utils.generic import generic_constants as gcst

logger = get_logger(__name__)

HISTORICAL_PERIOD_SCORE_TIME_DECAYING_FACTOR = 0.5  # to be fine-tuned


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
        - Prioritize contenders with the highest time-decayed PERIOD_SCORE (best recent performance).
    For synthetic queries:
        - Prioritize contenders with the least TOTAL_REQUESTS_MADE (need more assessment).

    If there are not enough contenders, fill the gaps by selecting miners with the least TOTAL_REQUESTS_MADE.

    Parameters:
        connection (Connection): The database connection.
        task (str): The task name.
        query_type (str): 'organic' or 'synthetic'.
        top_x (int): The number of contenders to fetch.

    Returns:
        List[Contender]: A list of Contender objects.
    """

    # Get current UTC timestamp
    now = datetime.now(timezone.utc)

    # Common SQL fragments
    base_select = f"""
        SELECT
            c.{dcst.CONTENDER_ID},
            c.{dcst.NODE_HOTKEY},
            c.{dcst.NODE_ID},
            c.{dcst.NETUID},
            c.{dcst.TASK},
            c.{dcst.RAW_CAPACITY},
            c.{dcst.CAPACITY_TO_SCORE},
            c.{dcst.CONSUMED_CAPACITY},
            c.{dcst.TOTAL_REQUESTS_MADE},
            c.{dcst.REQUESTS_429},
            c.{dcst.REQUESTS_500},
            c.{dcst.CAPACITY},
            c.{dcst.PERIOD_SCORE}
    """

    base_from = f"""
        FROM {dcst.CONTENDERS_TABLE} c
        JOIN {dcst.NODES_TABLE} n
            ON c.{dcst.NODE_ID} = n.{dcst.NODE_ID}
            AND c.{dcst.NETUID} = n.{dcst.NETUID}
        WHERE c.{dcst.TASK} = $1
            AND c.{dcst.CAPACITY} > 0
            AND n.{dcst.SYMMETRIC_KEY_UUID} IS NOT NULL
    """

    # Determine the ORDER BY clause based on the query type
    match query_type:
        case gcst.SYNTHETIC:
            # For synthetic queries, prioritize miners with least TOTAL_REQUESTS_MADE
            order_by = f"ORDER BY c.{dcst.TOTAL_REQUESTS_MADE} ASC"
            select_query = f"""
                {base_select}
                {base_from}
                {order_by}
                LIMIT $2
            """
            rows: list[dict[str, Any]] = await connection.fetch(
                select_query,
                task,
                top_x,
            )

        case gcst.ORGANIC:
            # For organic queries, calculate time-decayed PERIOD_SCORE in SQL
            decay_factor = HISTORICAL_PERIOD_SCORE_TIME_DECAYING_FACTOR  # e.g., 0.5
            scoring_period_time = ccst.SCORING_PERIOD_TIME  # Ensure this is in seconds

            # For organic queries, order by the decayed score
            order_by = "ORDER BY ds.decayed_score DESC NULLS LAST"

            # SQL query to calculate decayed score
            select_query = f"""
                WITH recent_scores AS (
                    SELECT
                        ch.{dcst.NODE_HOTKEY},
                        ch.{dcst.PERIOD_SCORE},
                        EXTRACT(EPOCH FROM ($3 - ch.{dcst.CREATED_AT})) AS time_diff
                    FROM {dcst.CONTENDERS_HISTORY_TABLE} ch
                    WHERE ch.{dcst.TASK} = $1
                ),
                decayed_scores AS (
                    SELECT
                        rs.{dcst.NODE_HOTKEY},
                        SUM(rs.{dcst.PERIOD_SCORE} * POWER({decay_factor}, rs.time_diff / {scoring_period_time})) AS decayed_score
                    FROM recent_scores rs
                    GROUP BY rs.{dcst.NODE_HOTKEY}
                )
                {base_select},
                ds.decayed_score
                {base_from}
                LEFT JOIN decayed_scores ds
                    ON c.{dcst.NODE_HOTKEY} = ds.{dcst.NODE_HOTKEY}
                {order_by}
                LIMIT $2
            """

            rows: list[dict[str, Any]] = await connection.fetch(
                select_query,
                task,
                top_x,
                now,
            )
        case _:
            raise ValueError(f"Invalid query type: {query_type}")

    # If not enough contenders are found, perform secondary selection
    if not rows or len(rows) < top_x:
        # Prepare a list of already selected contender IDs to avoid duplicates
        selected_contender_ids = [row[dcst.CONTENDER_ID] for row in rows]

        # Use parameterized query with ALL operator
        not_in_clause = f"AND c.{dcst.CONTENDER_ID} != ALL($3::text[])"

        secondary_order_by = f"ORDER BY c.{dcst.TOTAL_REQUESTS_MADE} ASC"
        secondary_select_query = f"""
            {base_select}
            {base_from}
            {not_in_clause}
            {secondary_order_by}
            LIMIT $2
        """

        secondary_rows: list[dict[str, Any]] = await connection.fetch(
            secondary_select_query,
            task,
            top_x - len(rows),
            selected_contender_ids,
        )

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
