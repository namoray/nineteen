from dataclasses import asdict
import json
from core.tasks import Task
from validator.db.src.sql.contenders import fetch_all_contenders, fetch_contender
from validator.db.src.database import PSQLDB
from validator.models import Contender
from validator.utils import redis_constants as rcst
from validator.utils import redis_utils as rutils, redis_dataclasses as rdc
from redis.asyncio import Redis
from core.logging import get_logger
import uuid

logger = get_logger(__name__)


def construct_synthetic_query_message(task: Task) -> str:
    return json.dumps(
        asdict(
            rdc.QueryQueueMessage(query_payload={}, query_type="synthetic", task=task.value, job_id=uuid.uuid4().hex)
        )
    )


# Consistently about 1ms
async def load_contender(psql_db: PSQLDB, contender_id: str) -> Contender | None:
    async with await psql_db.connection() as connection:
        return await fetch_contender(connection, contender_id)


async def load_contenders(psql_db: PSQLDB) -> list[Contender]:
    async with await psql_db.connection() as connection:
        return await fetch_all_contenders(connection)


# TODO: Might be able to get rid of it now
async def check_and_remove_contender_from_synthetics_if_finished(redis_db: Redis, contender_id: str) -> bool:
    if await rutils.check_value_is_in_set(redis_db, rcst.PARITICIPANT_IDS_TO_STOP_KEY, contender_id):
        logger.debug(f"Removing {contender_id} from synthetic queries")
        await rutils.remove_value_from_set(redis_db, rcst.PARITICIPANT_IDS_TO_STOP_KEY, contender_id)
        return True
    return False


async def add_synthetic_query_to_queue(redis_db: Redis, task: Task, max_length: int) -> None:
    message = construct_synthetic_query_message(task)
    await rutils.add_str_to_redis_list(redis_db, rcst.QUERY_QUEUE_KEY, message, max_length)


async def load_query_queue(redis_db: Redis) -> list[str]:
    return await rutils.get_redis_list(redis_db, rcst.QUERY_QUEUE_KEY)


async def load_synthetic_scheduling_queue(redis_db: Redis) -> list[str]:
    return await rutils.get_sorted_set(redis_db, rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY)
