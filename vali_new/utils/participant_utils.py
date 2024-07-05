from typing import List

from vali_new.models import Participant
from vali_new.utils import redis_constants as rcst
from vali_new.utils import redis_utils as rutils
from redis.asyncio import Redis


async def load_participant(redis_db: Redis, participant_id: str) -> Participant:
    participant_raw = await rutils.json_load_from_redis(redis_db, participant_id)
    participant = Participant(**participant_raw)
    return participant


async def load_participants(redis_db: Redis) -> List[Participant]:
    participant_ids_set = await redis_db.smembers(rcst.PARTICIPANT_IDS_KEY)

    participants = []
    for participant_id in (i.decode("utf-8") for i in participant_ids_set):
        participants.append(await load_participant(redis_db, participant_id))

    return participants
