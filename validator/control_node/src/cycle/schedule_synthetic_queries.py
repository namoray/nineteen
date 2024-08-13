"""
Schedules and processes synthetic queries for contenders.
Manages a queue of scheduled queries in Redis, executing them when due.
Provides performance metrics for the scheduling process.
"""

import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import os
import random
import time
from typing import Optional

from dotenv import load_dotenv
from validator.db.src.database import PSQLDB
from redis.asyncio import Redis
from validator.models import Contender
from validator.utils import contender_utils as putils
from validator.utils import redis_utils as rutils
from validator.utils import redis_constants as rcst
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Config:
    psql_db: PSQLDB
    redis_db: Redis
    run_once: bool
    test_env: bool


@dataclass
class PerformanceMetrics:
    processed_items: int = 0
    start_time: float = time.time()
    cumulative_late_time: float = 0
    cumulative_sleep_time: float = 0


@dataclass
class SyntheticQueueItem:
    contender_id: str
    delay: float


async def load_config() -> Config:
    load_dotenv()
    psql_db = PSQLDB()
    await psql_db.connect()
    redis_db = Redis(host=os.getenv("REDIS_HOST", "redis"))
    run_once = os.getenv("RUN_ONCE", "false").lower() == "true"
    test_env = os.getenv("ENV", "prod").lower() == "test"
    return Config(psql_db, redis_db, run_once, test_env)


async def _get_synthetic_queue_item(contender_id: str, delay: float) -> Optional[SyntheticQueueItem]:
    json_to_add = {
        "contender_id": contender_id,
        "delay": delay,
    }

    return SyntheticQueueItem(**json_to_add)


def _get_time_to_execute_query(delay: float) -> float:
    now = datetime.now()
    randomised_delay = max(delay, 0.1) * (0.90 + 0.10 * random.random())
    time_to_execute_query = now + timedelta(seconds=randomised_delay)
    return time_to_execute_query.timestamp()


async def _sleep_until_next_query(time_left_to_execute: float, metrics: "PerformanceMetrics") -> None:
    sleep_time = min(0.5, time_left_to_execute)
    metrics.cumulative_sleep_time += sleep_time
    await asyncio.sleep(sleep_time)


def _log_performance_metrics(metrics: "PerformanceMetrics") -> None:
    elapsed_time = time.time() - metrics.start_time
    processing_rate = metrics.processed_items / elapsed_time if elapsed_time > 0 else 0
    avg_late_time = metrics.cumulative_late_time / metrics.processed_items if metrics.processed_items > 0 else 0
    avg_sleep_time = metrics.cumulative_sleep_time / metrics.processed_items if metrics.processed_items > 0 else 0

    logger.debug("Performance metrics for synthetic scheduling processor:")
    logger.debug(f"  Processed items: {metrics.processed_items}")
    logger.debug(f"  Elapsed time: {elapsed_time:.2f} seconds")
    logger.debug(f"  Processing rate: {processing_rate:.2f} items/second")
    logger.debug(f"  Average late time: {avg_late_time:.4f} seconds/item")
    logger.debug(f"  Average sleep time: {avg_sleep_time:.4f} seconds/item")

    if avg_sleep_time < 1e-5 and elapsed_time > 5:
        logger.error("Average sleep time is ~0 - may not be keeping up with synthetic scheduling demand!")


async def schedule_synthetic_query(redis_db: Redis, contender_id: str, delay: float) -> None:
    synthetic_queue_item = await _get_synthetic_queue_item(contender_id, delay)
    time_to_execute_query = _get_time_to_execute_query(delay)
    await rutils.add_to_sorted_set(
        redis_db, rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY, data=asdict(synthetic_queue_item), score=time_to_execute_query
    )


async def schedule_initial_synthetics(config: Config, contenders: list[Contender]) -> None:
    await rutils.clear_sorted_set(config.redis_db, rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY)

    for contender in contenders:
        await schedule_synthetic_query(
            config.redis_db,
            contender.id,
            contender.delay_between_synthetic_requests,
        )

    logger.debug(f"Scheduled the first query for {len(contenders)} contenders")


async def remove_contender(config: Config, contender_id: str, delay: float) -> None:
    synthetic_queue_item = await _get_synthetic_queue_item(contender_id, delay)
    await rutils.remove_from_sorted_set(
        config.redis_db, rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY, asdict(synthetic_queue_item)
    )


async def reschedule_contender(
    config: Config, details: SyntheticQueueItem, metrics: PerformanceMetrics, overspilled_time: float
) -> None:
    contender_id = details.contender_id
    delay = details.delay

    requests_remaining = await putils.get_requests_remaining_and_decrement(config.psql_db, contender_id)
    if requests_remaining is None:
        logger.error(
            f"Could not find contender {contender_id} when trying to decrement synthetic requests remaining"
        )
        await remove_contender(config, contender_id, delay)

        return

    if requests_remaining == 0:
        logger.debug(f"Contender {contender_id} has no more requests remaining. Removing...")

        await remove_contender(config, contender_id, delay)
        return

    await putils.add_synthetic_query_to_queue(config.redis_db, contender_id)
    await schedule_synthetic_query(config.redis_db, contender_id, delay)
    metrics.cumulative_late_time += abs(overspilled_time)
    metrics.processed_items += 1


async def schedule_synthetics_until_done(config: Config) -> None:
    logger.debug(f"Scheduling any synthetic queries which are ready. Scheduling just once: {config.run_once}")

    pariticipants = await putils.load_contenders(config.psql_db)
    await schedule_initial_synthetics(config, pariticipants)

    if config.run_once:
        logger.debug("Only running once - exiting...")
        return

    metrics = PerformanceMetrics()
    log_interval = 1 if config.test_env else 60 * 1
    last_log_time = datetime.now().timestamp()

    logger.debug(f"Continually scheduling all queries. Logging every {log_interval} seconds.")
    while True:
        schedule_item = await rutils.get_first_from_sorted_set(config.redis_db, rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY)
        if schedule_item is None:
            logger.debug("schedule item is None, exiting...")
            break

        raw_details, timestamp = schedule_item
        current_time = datetime.now().timestamp()
        overspilled_time = timestamp - current_time

        if overspilled_time <= 0:
            await reschedule_contender(config, SyntheticQueueItem(**raw_details), metrics, overspilled_time)

        else:
            await _sleep_until_next_query(overspilled_time, metrics)

        if current_time - last_log_time >= log_interval:
            _log_performance_metrics(metrics)
            last_log_time = current_time


async def main() -> None:
    config = await load_config()
    try:
        await schedule_synthetics_until_done(config)
    finally:
        await config.psql_db.close()
        await config.redis_db.aclose()


if __name__ == "__main__":
    asyncio.run(main())
