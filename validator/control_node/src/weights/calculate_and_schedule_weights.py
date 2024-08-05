import asyncio
import json
import os
from dataclasses import dataclass, asdict

from redis.asyncio import Redis
from validator.db.src.database import PSQLDB
from validator.db.src import sql
from validator.utils import redis_constants as rcst
from validator.control_node.src.weights import calculations
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class Config:
    psql_db: PSQLDB
    redis_db: Redis
    netuid: int


async def load_config() -> Config:
    psql_db = PSQLDB()
    await psql_db.connect()
    redis_db = Redis(host="redis")
    netuid = int(os.getenv("NETUID", 19))
    return Config(psql_db=psql_db, redis_db=redis_db, netuid=netuid)


async def process_weights(config: Config):
    async with await config.psql_db.connection() as connection:
        participants = await sql.fetch_all_participants(connection, None)

    weights = await calculations.calculate_scores_for_settings_weights(config.psql_db, participants)
    await config.redis_db.rpush(rcst.WEIGHTS_TO_SET_QUEUE_KEY, json.dumps(asdict(weights)))
    logger.info("Weights calculated and pushed to Redis queue")


async def main():
    config = await load_config()
    try:
        await process_weights(config)
    finally:
        await config.psql_db.close()
        await config.redis_db.aclose()


if __name__ == "__main__":
    asyncio.run(main())
