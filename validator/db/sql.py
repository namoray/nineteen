from validator.db.database import PSQLDB
from core.bittensor_overrides import chain_data
from core.logging import get_logger

from asyncpg import Connection
from validator.models import Participant
from validator.utils import database_constants as dcst


logger = get_logger(__name__)


async def insert_axon_info(connection: Connection, axon_infos: list[chain_data.AxonInfo]) -> None:
    logger.debug(f"Inserting {len(axon_infos)} axon info records")
    await connection.executemany(
        f"""
        INSERT INTO {dcst.AXON_INFO_TABLE} (
            {dcst.HOTKEY},
            {dcst.COLDKEY},
            {dcst.AXON_VERSION},
            {dcst.IP},
            {dcst.PORT},
            {dcst.IP_TYPE},
            {dcst.AXON_UID},
            {dcst.INCENTIVE},
            {dcst.CREATED_AT}
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
        """,
        [
            (
                axon_info.hotkey,
                axon_info.coldkey,
                axon_info.version,
                axon_info.ip,
                axon_info.port,
                axon_info.ip_type,
                axon_info.axon_uid,
                axon_info.incentive,
            )
            for axon_info in axon_infos
        ],
    )


async def migrate_axons_to_axon_history(connection: Connection) -> None:  # noqa: F821
    await connection.execute(
        f"""
        INSERT INTO {dcst.AXON_INFO_HISTORY_TABLE} (
            {dcst.HOTKEY},
            {dcst.COLDKEY},
            {dcst.AXON_VERSION},
            {dcst.IP},
            {dcst.PORT},
            {dcst.IP_TYPE},
            {dcst.AXON_UID},
            {dcst.INCENTIVE},
            {dcst.CREATED_AT}
        )
        SELECT
            {dcst.HOTKEY},
            {dcst.COLDKEY},
            {dcst.AXON_VERSION},
            {dcst.IP},
            {dcst.PORT},
            {dcst.IP_TYPE},
            {dcst.AXON_UID},
            {dcst.INCENTIVE},
            {dcst.CREATED_AT}
        FROM {dcst.AXON_INFO_TABLE}
    """
    )

    # Now delete the old table info
    await connection.execute(f"TRUNCATE TABLE {dcst.AXON_INFO_TABLE}")


async def get_axons(psql_db: PSQLDB) -> list[chain_data.AxonInfo]:
    axons = await psql_db.fetchall(
        f"SELECT {dcst.HOTKEY}, {dcst.COLDKEY}, {dcst.AXON_VERSION} as version,"
        f"{dcst.IP}, {dcst.PORT}, {dcst.IP_TYPE}, {dcst.AXON_UID}, {dcst.INCENTIVE}"
        f" FROM {dcst.AXON_INFO_TABLE}"
    )
    return [chain_data.AxonInfo(**axon) for axon in axons]


async def insert_participants(connection: Connection, participants: list[Participant], validator_hotkey: str) -> None:
    logger.debug(f"Inserting {len(participants)} participant records")

    await connection.executemany(
        f"""
        INSERT INTO {dcst.PARTICIPANTS_TABLE} (
            {dcst.PARTICIPANT_ID},
            {dcst.MINER_HOTKEY},
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
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,  NOW(), NOW())
        """,
        [
            (
                participant.id,
                participant.miner_hotkey,
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

    await connection.execute(f"TRUNCATE TABLE {dcst.PARTICIPANTS_TABLE}")


# TODO: Do we even need this? If we only need UIDS for setting weights
# We can just query the metagraph for these surely.

# from models.utility_models import HotkeyInfo
# async def insert_hotkey_info(psql_db: PSQLDB, hotkey_info: HotkeyInfo) -> None:
#     await psql_db.execute(
#         f"""
#         INSERT INTO {dcst.HOTKEY_INFO_TABLE} (
#             {dcst.HOTKEY},
#             {dcst.UID}
#         )
#         VALUES ($1, $2)
#         """,
#         hotkey_info.hotkey,
#         hotkey_info.uid,
#     )
