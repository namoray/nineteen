from typing import Any

import asyncpg
from asyncpg import Pool


class PSQLDB:
    def __init__(self, connection_string: str):
        self.connection_string: str = connection_string
        self.pool: Pool | None = None

    async def connect(self) -> None:
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
