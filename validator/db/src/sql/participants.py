from generic.tasks import Task
from generic.logging import get_logger

from asyncpg import Connection
from validator.models import Participant, PeriodScore
from validator.utils import database_constants as dcst

logger = get_logger(__name__)


async def insert_participants(connection: Connection, participants: list[Participant], validator_hotkey: str) -> None:
    logger.debug(f"Inserting {len(participants)} participant records")

    await connection.executemany(
        f"""
        INSERT INTO {dcst.PARTICIPANTS_TABLE} (
            {dcst.PARTICIPANT_ID},
            {dcst.MINER_HOTKEY},
            {dcst.MINER_UID},
            {dcst.TASK},
            {dcst.VALIDATOR_HOTKEY},
            {dcst.CAPACITY},
            {dcst.CAPACITY_TO_SCORE},
            {dcst.CONSUMED_CAPACITY},
            {dcst.DELAY_BETWEEN_SYNTHETIC_REQUESTS},
            {dcst.SYNTHETIC_REQUESTS_STILL_TO_MAKE},
            {dcst.TOTAL_REQUESTS_MADE},
            {dcst.REQUESTS_429},
            {dcst.REQUESTS_500},
            {dcst.RAW_CAPACITY},
            {dcst.CREATED_AT},
            {dcst.UPDATED_AT}
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW(), NOW())
        """,
        [
            (
                participant.id,
                participant.miner_hotkey,
                participant.miner_uid,
                participant.task.value,
                validator_hotkey,
                participant.capacity,
                participant.capacity_to_score,
                participant.consumed_capacity,
                participant.delay_between_synthetic_requests,
                participant.synthetic_requests_still_to_make,
                participant.total_requests_made,
                participant.requests_429,
                participant.requests_500,
                participant.raw_capacity,
            )
            for participant in participants
        ],
    )


async def migrate_participants_to_participant_history(connection: Connection) -> None:
    await connection.execute(
        f"""
        INSERT INTO {dcst.PARTICIPANTS_HISTORY_TABLE} (
            {dcst.PARTICIPANT_ID},
            {dcst.MINER_HOTKEY},
            {dcst.MINER_UID},
            {dcst.TASK},
            {dcst.VALIDATOR_HOTKEY},
            {dcst.CAPACITY},
            {dcst.CAPACITY_TO_SCORE},
            {dcst.CONSUMED_CAPACITY},
            {dcst.DELAY_BETWEEN_SYNTHETIC_REQUESTS},
            {dcst.SYNTHETIC_REQUESTS_STILL_TO_MAKE},
            {dcst.TOTAL_REQUESTS_MADE},
            {dcst.REQUESTS_429},
            {dcst.REQUESTS_500},
            {dcst.RAW_CAPACITY},
            {dcst.PERIOD_SCORE},
            {dcst.CREATED_AT},
            {dcst.UPDATED_AT}
        )
        SELECT
            {dcst.PARTICIPANT_ID},
            {dcst.MINER_HOTKEY},
            {dcst.MINER_UID},
            {dcst.TASK},
            {dcst.VALIDATOR_HOTKEY},
            {dcst.CAPACITY},
            {dcst.CAPACITY_TO_SCORE},
            {dcst.CONSUMED_CAPACITY},
            {dcst.DELAY_BETWEEN_SYNTHETIC_REQUESTS},
            {dcst.SYNTHETIC_REQUESTS_STILL_TO_MAKE},
            {dcst.TOTAL_REQUESTS_MADE},
            {dcst.REQUESTS_429},
            {dcst.REQUESTS_500},
            {dcst.RAW_CAPACITY},
            {dcst.PERIOD_SCORE},
            {dcst.CREATED_AT},
            {dcst.UPDATED_AT}
        FROM {dcst.PARTICIPANTS_TABLE}
        """
    )

    await connection.execute(f"DELETE FROM {dcst.PARTICIPANTS_TABLE}")


async def get_participant_for_task(connection: Connection, task: Task) -> Participant | None:
    row = await connection.fetchrow(
        f"""
        SELECT 
            {dcst.PARTICIPANT_ID}, {dcst.MINER_HOTKEY}, {dcst.MINER_UID},{dcst.TASK},
            {dcst.CAPACITY}, {dcst.CAPACITY_TO_SCORE}, {dcst.CONSUMED_CAPACITY}, 
            {dcst.DELAY_BETWEEN_SYNTHETIC_REQUESTS}, {dcst.SYNTHETIC_REQUESTS_STILL_TO_MAKE}, 
            {dcst.TOTAL_REQUESTS_MADE}, {dcst.REQUESTS_429}, {dcst.REQUESTS_500}, 
            {dcst.RAW_CAPACITY}, {dcst.PERIOD_SCORE}
        FROM {dcst.PARTICIPANTS_TABLE} 
        WHERE {dcst.TASK} = $1
        """,
        task.value,
    )
    if not row:
        return None
    return Participant(**row)


async def fetch_participant(connection: Connection, participant_id: str) -> Participant | None:
    row = await connection.fetchrow(
        f"""
        SELECT 
            {dcst.PARTICIPANT_ID}, {dcst.MINER_HOTKEY}, {dcst.MINER_UID},{dcst.TASK},
            {dcst.CAPACITY}, {dcst.CAPACITY_TO_SCORE}, {dcst.CONSUMED_CAPACITY}, 
            {dcst.DELAY_BETWEEN_SYNTHETIC_REQUESTS}, {dcst.SYNTHETIC_REQUESTS_STILL_TO_MAKE}, 
            {dcst.TOTAL_REQUESTS_MADE}, {dcst.REQUESTS_429}, {dcst.REQUESTS_500}, 
            {dcst.RAW_CAPACITY}, {dcst.PERIOD_SCORE}
        FROM {dcst.PARTICIPANTS_TABLE} 
        WHERE {dcst.PARTICIPANT_ID} = $1
        """,
        participant_id,
    )
    if not row:
        return None
    return Participant(**row)


# TODO: add netuid to participant?!
async def fetch_all_participants(connection: Connection, netuid: int | None = None) -> list[Participant]:
    base_query = f"""
        SELECT 
            {dcst.PARTICIPANT_ID}, {dcst.MINER_HOTKEY}, {dcst.MINER_UID}, {dcst.TASK}, 
            {dcst.CAPACITY}, {dcst.CAPACITY_TO_SCORE}, {dcst.CONSUMED_CAPACITY}, 
            {dcst.DELAY_BETWEEN_SYNTHETIC_REQUESTS}, {dcst.SYNTHETIC_REQUESTS_STILL_TO_MAKE}, 
            {dcst.TOTAL_REQUESTS_MADE}, {dcst.REQUESTS_429}, {dcst.REQUESTS_500}, 
            {dcst.RAW_CAPACITY}, {dcst.PERIOD_SCORE}
        FROM {dcst.PARTICIPANTS_TABLE}
        """
    if netuid is None:
        rows = await connection.fetch(base_query)
    else:
        rows = await connection.fetch(base_query + f" WHERE {dcst.NETUID} = $1", netuid)
    return [Participant(**row) for row in rows]


async def fetch_hotkey_scores_for_task(connection: Connection, task: Task, miner_hotkey: str) -> list[PeriodScore]:
    rows = await connection.fetch(
        f"""
        SELECT
            {dcst.MINER_HOTKEY} as hotkey,
            {dcst.TASK},
            {dcst.PERIOD_SCORE},
            {dcst.CONSUMED_CAPACITY},
            {dcst.CREATED_AT}
        FROM {dcst.PARTICIPANTS_HISTORY_TABLE}
        WHERE {dcst.TASK} = $1
        AND {dcst.MINER_HOTKEY} = $2
        ORDER BY {dcst.CREATED_AT} DESC
        """,
        task.value,
        miner_hotkey,
    )
    return [PeriodScore(**row) for row in rows]


async def update_participants_period_scores(connection: Connection, participants: list[Participant]) -> None:
    await connection.executemany(
        f"""
        UPDATE {dcst.PARTICIPANTS_TABLE}
        SET {dcst.PERIOD_SCORE} = $1
        WHERE {dcst.PARTICIPANT_ID} = $2
        """,
        [(participant.period_score, participant.id) for participant in participants],
    )


async def get_and_decrement_synthetic_request_count(connection: Connection, participant_id: str) -> int | None:
    """
    Asynchronously retrieves and decrements the synthetic request count for a given participant, setting it to 0 if
    it the consumed capacity is greater than the announced capacity.
    """

    result = await connection.fetchrow(
        f"""
        UPDATE {dcst.PARTICIPANTS_TABLE}
        SET {dcst.SYNTHETIC_REQUESTS_STILL_TO_MAKE} = 
            CASE 
                WHEN {dcst.CONSUMED_CAPACITY} > {dcst.CAPACITY} THEN 0
                ELSE GREATEST({dcst.SYNTHETIC_REQUESTS_STILL_TO_MAKE} - 1, 0)
            END
        WHERE {dcst.PARTICIPANT_ID} = $1
        RETURNING {dcst.SYNTHETIC_REQUESTS_STILL_TO_MAKE}
        """,
        participant_id,
    )

    if result:
        return result[dcst.SYNTHETIC_REQUESTS_STILL_TO_MAKE]
    else:
        return None
