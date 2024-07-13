import asyncio
from datetime import datetime, timedelta
import random

from vali_new.models import Participant
from redis.asyncio import Redis
from vali_new.utils import participant_utils as putils, redis_utils as rutils, redis_constants as rcst

from core.logging import get_logger

logger = get_logger(__name__)


async def schedule_synthetic_queries_for_all_participants(
    redis_db: Redis,
) -> None:
    participants = await putils.load_participants(redis_db)
    for participant in participants:
        await putils.add_synthetic_query_to_queue(redis_db, participant.id)
    logger.debug(f"Added {len(participants)} for scheduling")


async def schedule_synthetic_queries_for_participant(redis_db: Redis, participant_id: Participant) -> None:
    participant = await putils.load_participant(redis_db, participant_id)
    delay = participant.delay_between_synthetic_requests

    for i in range(participant.synthetic_requests_still_to_make):
        now = datetime.now()
        randomised_delay = delay * (0.95 + 0.05 * random.random())
        time_to_execute_query = now + timedelta(seconds=randomised_delay)
        await schedule_synthetic_query(redis_db, participant_id, time_to_execute_query.timestamp())


async def schedule_synthetic_query(redis_db: Redis, participant_id: Participant, timestamp: float) -> None:
    json_to_add = {"participant_id": participant_id}
    await rutils.add_to_sorted_set(
        redis_db, rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY, data=json_to_add, score=timestamp
    )
    logger.debug(f"Added {json_to_add} to synthetic scheduling queue")


async def main():
    redis_db = Redis()
    redis_db
    ...


if __name__ == "__main__":
    asyncio.run(main())
