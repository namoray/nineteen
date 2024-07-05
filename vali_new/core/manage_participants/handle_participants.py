import asyncio
import collections
import random
from typing import Dict, List

from core import Task
import bittensor as bt
from validation.models import HotkeyRecord, UidRecordsForTask
from core import tasks
from validation.proxy.utils import query_utils
from validation.db.db_management import db_manager
from vali_new.utils import redis_constants as rcst
from vali_new.utils import redis_utils
from redis.asyncio import Redis


def calculate_period_scores_for_uids(uid_records_for_tasks: UidRecordsForTask) -> None:
    for task in uid_records_for_tasks:
        for record in uid_records_for_tasks[task].values():
            record.calculate_period_score()


async def store_period_scores(uid_records_for_tasks: UidRecordsForTask, validator_hotkey: str) -> None:
    for uid_records in uid_records_for_tasks.values():
        for uid_record in uid_records.values():
            await db_manager.insert_uid_record(uid_record, validator_hotkey)


def _get_percentage_of_tasks_to_score():
    return 1


async def handle_task_scoring_for_uid(
    redis_db: Redis,
    task: Task,
    hotkey: str,
    declared_volume: float,
    volume_to_score: float,
    number_of_requests_to_make: int,
    delay_between_requests: float,
) -> None:
    """
    Calculates volume to score
    Calculates number of synthetic requests off the back of that
    Creates a uid record & stores it
    Calculates delay between requests

    Add a marker to redis between the delays to send a request
    """

    uid_record = HotkeyRecord(
        hotkey=hotkey,
        task=task,
        synthetic_requests_still_to_make=number_of_requests_to_make,
        declared_volume=declared_volume,
    )
    # replace below with
    # self.uid_records_for_tasks[task][hotkey] = uid_record

    i = 0
    while uid_record.synthetic_requests_still_to_make > 0:
        # Random perturbation(s) to make sure we dont burst all requests at once
        if i == 0:
            random_factor = random.random()
        else:
            random_factor = random.random() * 0.05 + 0.95

        await asyncio.sleep(delay_between_requests * random_factor)

        synthetic_query_to_add = {"task": task, "hotkey": hotkey}
        await redis_utils.add_json_to_redis_list(redis_db, rcst.SYNTHETIC_QUERIES_TO_MAKE_KEY, synthetic_query_to_add)

        # Organic queries consume volume too, so it's possible we enough that we don't
        # Need synthetics anymore
        if uid_record.consumed_volume >= volume_to_score:
            break


async def start_synthetic_scoring(
    redis_db: Redis,
    capacities_for_tasks: Dict[Task, Dict[str, float]],
    task_to_hotkey_queue: Dict[Task, query_utils.UIDQueue],
) -> None:
    synthetic_scoring_tasks = []
    for task in Task:
        task_to_hotkey_queue[task] = query_utils.UIDQueue()
        for hotkey, declared_volume in capacities_for_tasks.get(task, {}).items():
            volume_to_score, number_of_requests_to_make, delay_between_requests = calculate_synthetic_query_parameters(
                task, declared_volume
            )
            if volume_to_score == 0:
                continue
            synthetic_scoring_tasks.append(
                asyncio.create_task(
                    handle_task_scoring_for_uid(
                        redis_db,
                        task,
                        hotkey,
                        declared_volume,
                        volume_to_score,
                        number_of_requests_to_make,
                        delay_between_requests,
                    )
                )
            )
    bt.logging.info(f"Starting querying for {len(synthetic_scoring_tasks)} tasks 🔥")
    return synthetic_scoring_tasks


class UidManager:
    def __init__(
        self,
        redis_db: Redis,
    ) -> None:
        self.redis_db = redis_db
        # Replace with redis?
        self.uid_records_for_tasks: UidRecordsForTask = collections.defaultdict(dict)
        self.synthetic_scoring_tasks: List[asyncio.Task] = []
        self.task_to_hotkey_queue: Dict[Task, query_utils.UIDQueue] = {}

    async def collect_synthetic_scoring_results(self) -> None:
        await asyncio.gather(*self.synthetic_scoring_tasks)

    async def start_period(self) -> None:
        # Get the participant info from redis

        # Store each participant info in redis somehow
        ...


async def main():
    redis_db = Redis()
    uid_manager = UidManager(
        capacities_for_tasks={tasks.Task.chat_mixtral: {1: 1_000_000}},
        validator_hotkey="123",
        is_testnet=True,
        redis_db=redis_db,
    )

    def patched_percentage_tasks_to_score():
        return 1

    uid_manager._get_percentage_of_tasks_to_score = patched_percentage_tasks_to_score
    await uid_manager.start_synthetic_scoring()
    await uid_manager.collect_synthetic_scoring_results()


if __name__ == "__main__":
    asyncio.run(main())
