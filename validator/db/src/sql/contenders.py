from fiber.logging_utils import get_logger

from asyncpg import Connection
from validator.db.src.database import PSQLDB
from validator.models import Contender, PeriodScore, calculate_period_score, ContenderSelectionInfo
from validator.utils.database import database_constants as dcst

logger = get_logger(__name__)


async def insert_contenders(connection: Connection, contenders: list[Contender], validator_hotkey: str) -> None:
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


async def get_contenders_for_selection(connection: Connection, task: str) -> list[ContenderSelectionInfo]:
    rows = await connection.fetch(
        f"""
        WITH contenders AS (
            SELECT 
                c.{dcst.CONTENDER_ID}, c.{dcst.NODE_HOTKEY}, c.{dcst.NODE_ID}, c.{dcst.TASK},
                c.{dcst.RAW_CAPACITY}, c.{dcst.CAPACITY_TO_SCORE}, c.{dcst.CONSUMED_CAPACITY},
                c.{dcst.TOTAL_REQUESTS_MADE}, c.{dcst.REQUESTS_429}, c.{dcst.REQUESTS_500}, 
                c.{dcst.CAPACITY}, c.{dcst.PERIOD_SCORE}, c.{dcst.NETUID}, c.{dcst.VALIDATOR_HOTKEY}
            FROM {dcst.CONTENDERS_TABLE} c
            JOIN {dcst.NODES_TABLE} n ON c.{dcst.NODE_ID} = n.{dcst.NODE_ID} AND c.{dcst.NETUID} = n.{dcst.NETUID}
            WHERE c.{dcst.TASK} = $1 
            AND c.{dcst.CAPACITY} > 0 
            AND n.{dcst.SYMMETRIC_KEY_UUID} IS NOT NULL
        ),
        contenders_weights_stats AS (
            SELECT {dcst.NETUID}, {dcst.TASK}, {dcst.NODE_HOTKEY}, {dcst.VALIDATOR_HOTKEY}, 
            {dcst.COLUMN_COMBINED_QUALITY_SCORE}, {dcst.COLUMN_NORMALISED_NET_SCORE}
            ROW_NUMBER() OVER (
                        PARTITION BY {dcst.NETUID}, {dcst.TASK}, {dcst.NODE_HOTKEY}, {dcst.VALIDATOR_HOTKEY}
                        ORDER BY {dcst.CREATED_AT} DESC
                        ) AS rank
            FROM {dcst.CONTENDERS_WEIGHTS_STATS_TABLE}
        ),
        last_contender_weights_stats AS (
            SELECT * FROM contenders_weights_stats WHERE rank = 1
        )
        SELECT c.*, s.{dcst.COLUMN_COMBINED_QUALITY_SCORE}
        FROM contenders c
        LEFT JOIN last_contender_weights_stats s
        -- be as explict as possible with the join conditions
        ON c.{dcst.NETUID} = s.{dcst.NETUID} AND c.{dcst.TASK} = s.{dcst.TASK} 
        AND c.{dcst.NODE_HOTKEY} = s.{dcst.NODE_HOTKEY} AND c.{dcst.VALIDATOR_HOTKEY} = s.{dcst.VALIDATOR_HOTKEY}
        """,
        task,
    )
    return [ContenderSelectionInfo(**row) for row in rows]


async def update_contender_capacities(psql_db: PSQLDB, contender: Contender, capacitity_consumed: float) -> None:
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


async def fetch_contender(connection: Connection, contender_id: str) -> Contender | None:
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


async def fetch_all_contenders(connection: Connection, netuid: int | None = None) -> list[Contender]:
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


async def fetch_hotkey_scores_for_task(connection: Connection, task: str, node_hotkey: str) -> list[PeriodScore]:
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


async def get_and_decrement_synthetic_request_count(connection: Connection, contender_id: str) -> int | None:
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
