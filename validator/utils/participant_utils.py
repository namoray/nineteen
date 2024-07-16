import json
from vali_new.models import Participant
from vali_new.utils import redis_constants as rcst
from vali_new.utils import redis_utils as rutils
from redis.asyncio import Redis
from core.logging import get_logger


logger = get_logger(__name__)


def construct_synthetic_query_message(participant_id: str) -> str:
    return json.dumps({"query_type": "synthetic", "query_payload": {"participant_id": participant_id}})


async def load_participant(redis_db: Redis, participant_id: str) -> Participant:
    participant_raw = await rutils.json_load_from_redis(redis_db, participant_id)
    participant = Participant(**participant_raw)
    return participant


async def load_participants(redis_db: Redis) -> list[Participant]:
    participant_ids_set = await redis_db.smembers(rcst.PARTICIPANT_IDS_KEY)

    participants = []
    for participant_id in (i.decode("utf-8") for i in participant_ids_set):
        participants.append(await load_participant(redis_db, participant_id))

    return participants


# TODO: Might be able to get rid of it now
async def check_and_remove_participant_from_synthetics_if_finished(redis_db: Redis, participant_id: str) -> bool:
    if await rutils.check_value_is_in_set(redis_db, rcst.PARITICIPANT_IDS_TO_STOP_KEY, participant_id):
        logger.debug(f"Removing {participant_id} from synthetic queries")
        await rutils.remove_value_from_set(redis_db, rcst.PARITICIPANT_IDS_TO_STOP_KEY, participant_id)
        return True
    return False


async def add_synthetic_query_to_queue(redis_db: Redis, participant_id: str) -> None:
    message = construct_synthetic_query_message(participant_id)
    await rutils.add_str_to_redis_list(redis_db, rcst.QUERY_QUEUE_KEY, message)


async def load_query_queue(redis_db: Redis) -> list[str]:
    return await rutils.get_redis_list(redis_db, rcst.QUERY_QUEUE_KEY)


async def load_synthetic_scheduling_queue(redis_db: Redis) -> list[str]:
    return await rutils.get_sorted_set(redis_db, rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY)
