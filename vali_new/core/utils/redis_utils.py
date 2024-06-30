from typing import Any, Dict
from redis.asyncio import Redis
import json


async def load_json_from_redis(redis_db: Redis, key: str) -> Dict[Any, Any]:
    raw_json = await redis_db.get(key)
    if raw_json is None:
        json_obj = {}
    else:
        json_obj = json.loads(raw_json)
    return json_obj
