from validator.db.database import PSQLDB
from core.bittensor_overrides import chain_data
from core.logging import get_logger

from asyncpg import Connection
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
            {dcst.NETUID},
            {dcst.NETWORK},
            {dcst.STAKE},
            {dcst.CREATED_AT}
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW())
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
                axon_info.netuid,
                axon_info.network,
                axon_info.stake,
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
            {dcst.NETUID},
            {dcst.NETWORK},
            {dcst.STAKE},
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
            {dcst.NETUID},
            {dcst.NETWORK},
            {dcst.STAKE},
            {dcst.CREATED_AT}
        FROM {dcst.AXON_INFO_TABLE}
    """
    )

    # Now delete the old table info
    await connection.execute(f"TRUNCATE TABLE {dcst.AXON_INFO_TABLE}")


async def get_axons(psql_db: PSQLDB) -> list[chain_data.AxonInfo]:
    axons = await psql_db.fetchall(
        f"SELECT {dcst.HOTKEY}, {dcst.COLDKEY}, {dcst.AXON_VERSION} as version,"
        f"{dcst.IP}, {dcst.PORT}, {dcst.IP_TYPE}, {dcst.AXON_UID}, {dcst.INCENTIVE},",
        f"{dcst.NETUID}, {dcst.NETWORK}, {dcst.STAKE}" f" FROM {dcst.AXON_INFO_TABLE}",
    )
    return [chain_data.AxonInfo(**axon) for axon in axons]
