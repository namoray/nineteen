import asyncio
from datetime import datetime, timedelta
import random

from validator.models import Participant
from redis.asyncio import Redis
from validator.utils import participant_utils as putils, redis_utils as rutils, redis_constants as rcst

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
    # Need timestamp to keep it unique
    json_to_add = {"participant_id": participant_id, "timestamp": timestamp}
    await rutils.add_to_sorted_set(redis_db, rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY, data=json_to_add, score=timestamp)
    logger.debug(f"Added {json_to_add} to synthetic scheduling queue")


async def run_schedule_processor(redis_db: Redis, run_once: bool = False) -> None:
    """
    Continuously checks the sorted set for synthetic queries to schedule.
    It polls the latest (lowest timestamp). Calculates the 'time left to execute',
    which is the difference between the current time and the timestamp of the query.
    if it is < 0 then add the value to the query queue and continue
    if it is > 0 then sleep min(0.5, time left to execute + 0.01) seconds

    run_once is used for testing purposes to only update the queue with one 'batch'
    """
    while (
        earliest_query := await rutils.get_first_from_sorted_set(redis_db, rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY)
    ) is not None:
        current_time = datetime.now().timestamp()
        time_left_to_execute = earliest_query["timestamp"] - current_time

        if time_left_to_execute <= 0:
            await rutils.remove_from_sorted_set(redis_db, rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY, earliest_query)
            await putils.add_synthetic_query_to_queue(redis_db, earliest_query["participant_id"])
            logger.debug(f"Added to the query queue for participant {earliest_query['participant_id']}")
        else:
            sleep_time = min(0.5, time_left_to_execute + 0.01)
            if run_once:
                break
            await asyncio.sleep(sleep_time)


async def main():
    redis_db = Redis()
    redis_db
    ...


if __name__ == "__main__":
    asyncio.run(main())
