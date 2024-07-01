from typing import Any, Dict
from redis.asyncio import Redis
import json
from enum import Enum


def _remove_enums(map: Dict[Any, Any]) -> Dict[Any, Any]:
    for k, v in zip(list(map.keys()), list(map.values())):
        if isinstance(k, Enum):
            map[k.value] = v
            del map[k]
        if isinstance(v, Enum):
            map[k] = v.value
    return map


async def load_json_from_redis(redis_db: Redis, key: str, default: Any = {}) -> Dict[Any, Any]:
    raw_json = await redis_db.get(key)
    if raw_json is None:
        json_obj = default
    else:
        json_obj = json.loads(raw_json)
    return json_obj


async def save_json_to_redis(redis_db: Redis, key: str, json_to_save: Dict[Any, Any]) -> None:
    # Convert Task to Task.value, etc
    json_to_save = _remove_enums(json_to_save)
    json_string = json.dumps(json_to_save)
    await redis_db.set(key, json_string)


async def add_json_to_list_in_redis(redis_db: Redis, key: str, json_to_add: Dict[Any, Any]) -> None:
    # Convert Task to Task.value, etc
    json_to_add = _remove_enums(json_to_add)
    json_string = json.dumps(json_to_add)

    raw_existing_list = await redis_db.get(key)
    if raw_existing_list is None:
        existing_list = []
    else:
        existing_list = json.loads(raw_existing_list)

    existing_list.append(json_string)
    dumped_list = json.dumps(existing_list)
    await redis_db.set(key, dumped_list)
