import asyncio
from datetime import datetime, timedelta
import os
import random

from validator.db.database import PSQLDB
from redis.asyncio import Redis
from validator.utils import participant_utils as putils, redis_utils as rutils, redis_constants as rcst

from core.logging import get_logger

logger = get_logger(__name__)


def _log_scheduling_details_in_human_readable(participant_id: str, delay: float, timestamp: float) -> None:
    if os.getenv("ENV") != "prod":
        human_readable_time1 = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        logger.debug(
            f"Found a query with score: {human_readable_time1}. New synthetic query for participant {participant_id}"
            f" with delay of {delay}"
        )


def _get_time_to_execute_query(delay: float) -> float:
    now = datetime.now()
    randomised_delay = delay * (0.90 + 0.10 * random.random())
    time_to_execute_query = now + timedelta(seconds=randomised_delay)
    return time_to_execute_query.timestamp()


async def schedule_synthetic_queries_for_all_participants(psql_db: PSQLDB, redis_db: Redis) -> None:
    participants = await putils.load_participants(psql_db)
    for participant in participants:
        await schedule_synthetic_query(redis_db, participant.id, participant.delay_between_synthetic_requests)
    logger.debug(f"Added {len(participants)} for scheduling")


async def schedule_synthetic_query(redis_db: Redis, participant_id: str, delay: float) -> None:
    # Need timestamp to keep it unique
    json_to_add = {
        "participant_id": participant_id,
        "delay": delay,
    }
    time_to_execute_query = _get_time_to_execute_query(delay)
    await rutils.add_to_sorted_set(
        redis_db, rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY, data=json_to_add, score=time_to_execute_query
    )


async def run_schedule_processor(redis_db: Redis, run_once: bool = False) -> None:
    """
    Continuously checks the sorted set for synthetic queries to schedule.
    It polls the latest (lowest timestamp). Calculates the 'time left to execute',
    which is the difference between the current time and the timestamp of the query.
    if it is < 0 then add the value to the query queue and continue
    if it is > 0 then sleep min(0.5, time left to execute + 0.01) seconds

    run_once is used for testing purposes to only update the queue with one 'batch'
    """
    logger.debug(f"Scheduling any synthetic queries which are ready. Scheduling just once: {run_once}")
    while (
        schedule_item := await rutils.get_first_from_sorted_set(redis_db, rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY)
    ) is not None:
        details, timestamp = schedule_item
        current_time = datetime.now().timestamp()
        time_left_to_execute = timestamp - current_time

        if time_left_to_execute <= 0:
            await putils.add_synthetic_query_to_queue(redis_db, details["participant_id"])

            _log_scheduling_details_in_human_readable(details["participant_id"], details["delay"], timestamp)

            await schedule_synthetic_query(redis_db, **details)
            logger.debug(f"Added to the query queue for participant {details['participant_id']}")
        else:
            sleep_time = min(0.5, time_left_to_execute + 0.01)
            if run_once:
                break
            await asyncio.sleep(sleep_time)


async def main():
    redis_db = Redis(host="redis")
    psql_db = PSQLDB()
    await psql_db.connect()

    await schedule_synthetic_queries_for_all_participants(psql_db, redis_db)
    await run_schedule_processor(redis_db, run_once=False)


if __name__ == "__main__":
    asyncio.run(main())
