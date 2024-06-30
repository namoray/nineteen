from typing import Any, Dict
from redis.asyncio import Redis
import json
from enum import Enum


async def load_json_from_redis(redis_db: Redis, key: str) -> Dict[Any, Any]:
    raw_json = await redis_db.get(key)
    if raw_json is None:
        json_obj = {}
    else:
        json_obj = json.loads(raw_json)
    return json_obj


async def save_json_to_redis(redis_db: Redis, key: str, json_to_save: Dict[Any, Any]) -> None:
    # Convert Task to Task.value, etc
    for k, v in zip(list(json_to_save.keys()), list(json_to_save.values())):
        if isinstance(k, Enum):
            json_to_save[k.value] = v
            del json_to_save[k]
    json_string = json.dumps(json_to_save)
    await redis_db.set(key, json_string)


async def add_json_to_list_in_redis(redis_db: Redis, key: str, json_to_add: Dict[Any, Any]) -> None:
    # Convert Task to Task.value, etc
    for k, v in zip(list(json_to_add.keys()), list(json_to_add.values())):
        if isinstance(k, Enum):
            json_to_add[k.value] = v
            del json_to_add[k]
    json_string = json.dumps(json_to_add)

    raw_existing_list = await redis_db.get(key)
    if raw_existing_list is None:
        existing_list = []
    else:
        existing_list = json.loads(raw_existing_list)

    existing_list.append(json_string)
    dumped_list = json.dumps(existing_list)
    await redis_db.set(key, dumped_list)
