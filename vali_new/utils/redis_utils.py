from typing import Any, Dict
from redis.asyncio import Redis
import json
from enum import Enum


def _remove_enums(map: Dict[Any, Any]) -> Dict[Any, Any]:
    # Convert Task to Task.value, etc
    for k, v in zip(list(map.keys()), list(map.values())):
        if isinstance(k, Enum):
            map[k.value] = v
            del map[k]
        if isinstance(v, Enum):
            map[k] = v.value
    return map


async def json_load_from_redis(redis_db: Redis, key: str, default: Any = {}) -> Dict[Any, Any]:
    raw_json = await redis_db.get(key)
    if raw_json is None:
        json_obj = default
    else:
        json_obj = json.loads(raw_json)

    return json_obj


async def save_json_to_redis(
    redis_db: Redis, key: str, json_to_save: Dict[Any, Any], remove_enums: bool = True
) -> None:
    if remove_enums:
        json_to_save = _remove_enums(json_to_save)
    json_string = json.dumps(json_to_save)
    await redis_db.set(key, json_string)


async def add_json_to_redis_list(redis_db: Redis, queue: str, json_to_add: Dict[Any, Any]) -> None:
    json_to_add = _remove_enums(json_to_add)
    json_string = json.dumps(json_to_add)

    await redis_db.rpush(queue, json_string)