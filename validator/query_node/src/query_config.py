from dataclasses import dataclass
import httpx
from core.log import get_logger
from validator.db.src.database import PSQLDB
from redis.asyncio import Redis

logger = get_logger(__name__)


@dataclass
class Config:
    psql_db: PSQLDB
    redis_db: Redis
    ss58_address: str
    netuid: int
    httpx_client: httpx.AsyncClient = httpx.AsyncClient()
    replace_with_localhost: bool = False
    replace_with_docker_localhost: bool = True
