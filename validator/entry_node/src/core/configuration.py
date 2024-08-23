import os

from dotenv import load_dotenv
from typing import TypeVar
from pydantic import BaseModel
from redis.asyncio import Redis
from aiocache import cached
from validator.db.src.database import PSQLDB

T = TypeVar("T", bound=BaseModel)

load_dotenv()

from dataclasses import dataclass


@dataclass
class Config:
    redis_db: Redis
    psql_db: PSQLDB


@cached(ttl=None)
async def factory_config() -> Config:
    localhost = bool(os.getenv("LOCALHOST", "false").lower() == "true")
    if localhost:
        redis_host = "localhost"
        os.environ["POSTGRES_HOST"] = "localhost"
    else:
        redis_host = os.getenv("REDIS_HOST", "redis")

    psql_db = PSQLDB()
    await psql_db.connect()
    redis_db = Redis(host=redis_host)

    return Config(
        psql_db=psql_db,
        redis_db=redis_db,
    )
