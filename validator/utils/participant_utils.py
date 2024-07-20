import json
from validator.db import sql
from validator.db.database import PSQLDB
from validator.models import Participant
from validator.utils import redis_constants as rcst
from validator.utils import redis_utils as rutils
from redis.asyncio import Redis
from core.logging import get_logger


logger = get_logger(__name__)


def construct_synthetic_query_message(participant_id: str) -> str:
    return json.dumps({"query_type": "synthetic", "query_payload": {"participant_id": participant_id}})


# Consistently about 1ms
async def load_participant(psql_db: PSQLDB, participant_id: str) -> Participant:
    async with await psql_db.connection() as connection:
        return await sql.fetch_participant(connection, participant_id)


async def load_participants(psql_db: PSQLDB) -> list[Participant]:
    async with await psql_db.connection() as connection:
        return await sql.fetch_all_participants(connection)


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
