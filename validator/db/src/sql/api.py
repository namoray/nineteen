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
        """, (api_key, balance, rate_limit_per_minute, name)
    )
