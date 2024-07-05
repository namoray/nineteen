from typing import Any, Dict, List
from redis.asyncio import Redis
from vali_new.utils import redis_constants as rcst
import json
from enum import Enum
import copy

from vali_new.models import Participant

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

async def load_participants(redis_db: Redis) -> List[Participant]:
    participant_ids_set = await redis_db.smembers(rcst.PARTICIPANT_IDS_KEY)

    participants = []
    for participant_id in (i.decode("utf-8") for i in participant_ids_set):
        participant_raw = await json_load_from_redis(redis_db, participant_id)
        participant = Participant(**participant_raw)
        participants.append(participant)
    
    return participants
