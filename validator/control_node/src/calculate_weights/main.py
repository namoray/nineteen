# Still need to do calculations then send to redis


import asyncio
import json
import os
from validator.db.src.database import PSQLDB
from validator.db import sql
from validator.utils import redis_constants as rcst, redis_dataclasses as rdc
from redis.asyncio import Redis
from core.logging import get_logger
from dataclasses import asdict
from validator.core.calculate_weights import calculations

logger = get_logger(__name__)


async def main():
    psql_db = PSQLDB()
    await psql_db.connect()
    redis = Redis(host="redis")
    netuid = int(os.getenv("NETUID", 19))
    async with await psql_db.connection() as connection:
        participants = await sql.fetch_all_participants(connection, None)
    scores = await calculations.calculate_scores_for_settings_weights(psql_db, participants)

    await redis.rpush(rcst.WEIGHTS_TO_SET_QUEUE_KEY, json.dumps(asdict(weights)))
    return


if __name__ == "__main__":
    asyncio.run(main())
