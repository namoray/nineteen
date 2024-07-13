from db.database import PSQLDB
from core.bittensor_overrides import chain_data

from vali_new.utils import database_constants as dcst


async def insert_axon_info(psql_db: PSQLDB, axon_info: chain_data.AxonInfo) -> None:
    await psql_db.execute(
        f"""
        INSERT INTO {dcst.AXON_INFO_TABLE} (
            {dcst.HOTKEY},
            {dcst.COLDKEY}
            {dcst.VERSION},
            {dcst.IP},
            {dcst.PORT},
            {dcst.IP_TYPE},
        )
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        axon_info.hotkey,
        axon_info.coldkey,
        axon_info.version,
        axon_info.ip,
        axon_info.port,
        axon_info.ip_type,
    )


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
