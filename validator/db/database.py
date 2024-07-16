from typing import Any

import asyncpg
from asyncpg import Pool

from vali_new.utils import database_utils as dutils
from core.logging import get_logger

logger = get_logger(__name__)


class PSQLDB:
    def __init__(self, from_env: bool = True, connection_string: str | None = None):
        if from_env:
            connection_string = dutils.get_connection_string_from_env()
        elif connection_string is None:
            raise ValueError("Either from_env must be True or connection_string must be set")
        self.connection_string: str = connection_string
        self.pool: Pool | None = None

    async def connect(self) -> None:
        logger.debug(f"Connecting to {self.connection_string}")
        self.pool = await asyncpg.create_pool(self.connection_string)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        if not self.pool:
            raise RuntimeError("Database connection not established. Call connect() first.")
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        if not self.pool:
            raise RuntimeError("Database connection not established. Call connect() first.")
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        if not self.pool:
            raise RuntimeError("Database connection not established. Call connect() first.")
        async with self.pool.acquire() as connection:
            return await connection.execute(query, *args)

    async def fetchall(self, query: str, *args: Any) -> list[dict[str, Any]]:
        if not self.pool:
            raise RuntimeError("Database connection not established. Call connect() first.")
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(query, *args)
            return [dict(row) for row in rows]
