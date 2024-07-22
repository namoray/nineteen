import asyncio
from datetime import datetime, timedelta
import os
import random
import time

from validator.db.database import PSQLDB
from redis.asyncio import Redis
from validator.utils import (
    participant_utils as putils,
    redis_utils as rutils,
    redis_constants as rcst,
)
from core.logging import get_logger

logger = get_logger(__name__)


def _log_performance_metrics(
    processed_items: int, start_time: float, cumulative_late_time: float, cumulative_sleep_time: float
) -> None:
    elapsed_time: float = time.time() - start_time
    processing_rate: float = processed_items / elapsed_time if elapsed_time > 0 else 0
    avg_late_time: float = cumulative_late_time / processed_items if processed_items > 0 else 0
    avg_sleep_time: float = cumulative_sleep_time / processed_items if processed_items > 0 else 0

    logger.debug("Performance metrics for synthetic scheduling processor:")
    logger.debug(f"  Processed items: {processed_items}")
    logger.debug(f"  Elapsed time: {elapsed_time:.2f} seconds")
    logger.debug(f"  Processing rate: {processing_rate:.2f} items/second")
    logger.debug(f"  Average late time: {avg_late_time:.4f} seconds/item")
    logger.debug(f"  Average sleep time: {avg_sleep_time:.4f} seconds/item")

    # If we don't manage to keep up, then we may need to spawn multiple threads
    if avg_sleep_time < 1e-5 and elapsed_time > 5:
        logger.error("Average  sleep time is ~0 - may not be keeping up with synthetic scheduling demand!")


def _get_time_to_execute_query(delay: float) -> float:
    now = datetime.now()
    randomised_delay = delay * (0.90 + 0.10 * random.random())
    time_to_execute_query = now + timedelta(seconds=randomised_delay)
    return time_to_execute_query.timestamp()


async def schedule_synthetic_queries_for_all_participants(psql_db: PSQLDB, redis_db: Redis) -> None:
    await rutils.clear_sorted_set(redis_db, rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY)

    participants = await putils.load_participants(psql_db)
    for participant in participants:
        await schedule_synthetic_query(redis_db, participant.id, participant.delay_between_synthetic_requests)

        # Below for load testing

        # for i in range(100):
        #     await schedule_synthetic_query(
        #         redis_db, participant.id + str(i), participant.delay_between_synthetic_requests
        #     )

    logger.debug(f"Scheduled the first query for {len(participants)} ")


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
    logger.debug(f"Scheduling any synthetic queries which are ready. Scheduling just once: {run_once}")

    processed_items: int = 0
    start_time: float = time.time()
    cumulative_late_time: float = 0
    cumulative_sleep_time: float = 0

    while (
        schedule_item := await rutils.get_first_from_sorted_set(redis_db, rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY)
    ) is not None:
        details, timestamp = schedule_item
        current_time: float = datetime.now().timestamp()
        time_left_to_execute: float = timestamp - current_time

        if time_left_to_execute <= 0:
            cumulative_late_time += abs(time_left_to_execute)
            await putils.add_synthetic_query_to_queue(redis_db, details["participant_id"])
            await schedule_synthetic_query(redis_db, **details)
            processed_items += 1
        else:
            logger.debug(f"No queries ready; Time left to execute next: {time_left_to_execute}")
            sleep_time: float = min(0.5, time_left_to_execute)
            cumulative_sleep_time += sleep_time
            if run_once:
                break
            await asyncio.sleep(sleep_time)

        if processed_items % 10 == 0 and processed_items > 0:
            _log_performance_metrics(processed_items, start_time, cumulative_late_time, cumulative_sleep_time)


async def main():
    redis_db = Redis(host="redis")
    psql_db = PSQLDB()

    run_once = os.getenv("RUN_ONCE", "true").lower() == "true"
    test = os.getenv("ENV", "prod").lower() == "test"
    await psql_db.connect()
    specific_participant = os.getenv("PARTICIPANT_ID", None)
    if specific_participant is not None:
        await putils.add_synthetic_query_to_queue(redis_db, specific_participant)

    else:
        await schedule_synthetic_queries_for_all_participants(psql_db, redis_db)
        if test:
            logger.debug("Sleeping for a few secs to let some synthetics build up...")
            await asyncio.sleep(3)
        await run_schedule_processor(redis_db, run_once=run_once)


if __name__ == "__main__":
    asyncio.run(main())
