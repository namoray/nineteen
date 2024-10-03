from fiber.logging_utils import get_logger

from asyncpg import Connection
from validator.utils.database import database_constants as dcst

logger = get_logger(__name__)


async def add_api_key(connection: Connection, api_key: str, balance: int, rate_limit_per_minute: int, name: str) -> None:
    await connection.execute(
        f"""
        INSERT INTO {dcst.API_KEYS_TABLE} (
            {dcst.KEY},
            {dcst.BALANCE},
            {dcst.RATE_LIMIT_PER_MINUTE},
            {dcst.NAME}
        ) VALUES ($1, $2, $3, $4)
        """,
        api_key,
        balance,
        rate_limit_per_minute,
        name,
    )


async def update_api_key_balance(connection: Connection, api_key: str, balance: int) -> None:
    await connection.execute(
        f"""
        UPDATE {dcst.API_KEYS_TABLE} SET
            {dcst.BALANCE} = $1
        WHERE {dcst.KEY} = $2
        """,
        balance,
        api_key,
    )

async def update_api_key_rate_limit_per_minute(connection: Connection, api_key: str, rate_limit_per_minute: int) -> None:
    await connection.execute(
        f"""
        UPDATE {dcst.API_KEYS_TABLE} SET
            {dcst.RATE_LIMIT_PER_MINUTE} = $1
        WHERE {dcst.KEY} = $2
        """,
        rate_limit_per_minute,
        api_key,
    ) 

async def update_api_key_name(connection: Connection, api_key: str, name: str) -> None:
    await connection.execute(
        f"""
        UPDATE {dcst.API_KEYS_TABLE} SET
            {dcst.NAME} = $1
        WHERE {dcst.KEY} = $2
        """,
        name,
        api_key,
    )   


async def delete_api_key(connection: Connection, api_key: str) -> None:
    await connection.execute(
        f"""
        DELETE FROM {dcst.API_KEYS_TABLE} WHERE {dcst.KEY} = $1
        """,
        api_key,
    )
