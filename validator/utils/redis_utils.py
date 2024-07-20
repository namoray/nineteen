from typing import Any, Dict, List
from redis.asyncio import Redis
import json
from enum import Enum
import copy
from core.logging import get_logger

logger = get_logger(__name__)


def _remove_enums(map: Dict[Any, Any]) -> Dict[Any, Any]:
    # TODO: Does this need to be deep copy?
    map_copy = copy.copy(map)
    # Convert Task to Task.value, etc
    for k, v in zip(list(map.keys()), list(map.values())):
        if isinstance(k, Enum):
            map_copy[k.value] = v
            del map_copy[k]
        if isinstance(v, Enum):
            map_copy[k] = v.value
    return map_copy


async def delete_key_from_redis(redis_db: Redis, key: str) -> None:
    await redis_db.delete(key)


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


async def add_to_set_redis(redis_db: Redis, name: str, value: str) -> None:
    await redis_db.sadd(name, value)


async def add_json_to_redis_list(redis_db: Redis, queue: str, json_to_add: Dict[Any, Any]) -> None:
    json_to_add = _remove_enums(json_to_add)
    json_string = json.dumps(json_to_add)

    await redis_db.rpush(queue, json_string)


async def clear_sorted_set(redis_db: Redis, name: str) -> None:
    await redis_db.delete(name)


async def add_to_sorted_set(redis_db: Redis, name: str, data: str | dict[Any, Any], score: float) -> None:
    if isinstance(data, dict):
        json_to_add = _remove_enums(data)
        data = json.dumps(json_to_add)
    await redis_db.zadd(name, {data: score})


async def add_str_to_redis_list(redis_db: Redis, queue: str, value_to_add: str) -> None:
    await redis_db.rpush(queue, value_to_add)


async def get_redis_list(redis_db: Redis, queue: str) -> List[str]:
    return await redis_db.lrange(queue, 0, -1)


async def get_sorted_set(redis_db: Redis, name: str) -> List[str]:
    return await redis_db.zrevrange(name, 0, -1)


async def get_first_from_sorted_set(redis_db: Redis, key: str) -> tuple[dict[str, Any], float] | None:
    """
    Get the first (lowest scored) item from a Redis sorted set.

    :param redis_db: Redis connection
    :param key: The key of the sorted set
    :return: The first item as a dictionary, or None if the set is empty
    """
    result = await redis_db.zrange(key, 0, 0, withscores=True)
    if not result:
        return None

    item, score = result[0]
    try:
        return json.loads(item.decode("utf-8")), score
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from Redis: {item}")
        return None


async def remove_from_sorted_set(redis_db: Redis, key: str, data: Dict[str, Any]) -> None:
    """
    Remove an item from a Redis sorted set.

    :param redis_db: Redis connection
    :param key: The key of the sorted set
    :param data: The data to remove (should match the stored JSON string)
    """
    json_str = json.dumps(data)
    await redis_db.zrem(key, json_str)


async def check_value_is_in_set(redis_db: Redis, name: str, value) -> bool:
    return await redis_db.sismember(name, value)


async def remove_value_from_set(redis_db: Redis, name: str, value: str) -> None:
    await redis_db.srem(name, value)
