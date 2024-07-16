import socket
from typing import Any

import asyncpg
from asyncpg import Pool, PostgresError

from validator.utils import database_utils as dutils
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
        try:
            self.pool = await asyncpg.create_pool(self.connection_string)
            if self.pool is None:
                raise ConnectionError("Failed to create connection pool")
        except asyncpg.exceptions.PostgresError as e:
            raise ConnectionError(f"PostgreSQL error: {str(e)}") from e
        except socket.gaierror as e:
            raise ConnectionError(f"DNS resolution failed: {str(e)}. Check your host name.") from e
        except Exception as e:
            raise ConnectionError(f"Unexpected error while connecting: {str(e)}") from e

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    async def fetchall(self, query: str, *args: Any) -> list[dict[str, Any]]:
        if not self.pool:
            raise RuntimeError("Database connection not established. Call connect() first.")
        async with self.pool.acquire() as connection:
            try:
                rows = await connection.fetch(query, *args)
                return [dict(row) for row in rows]

            except asyncpg.exceptions.PostgresError as e:
                logger.error(f"PostgreSQL error in fetch_all: {str(e)}")
                logger.error(f"Query: {query}")
                raise

    async def connection(self) -> asyncpg.pool.PoolAcquireContext:
        if not self.pool:
            raise RuntimeError("Database connection not established. Call connect() first.")
        return self.pool.acquire()
