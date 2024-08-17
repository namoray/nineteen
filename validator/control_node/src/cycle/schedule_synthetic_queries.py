import asyncio
from dataclasses import dataclass
import datetime
import time
from typing import Dict, List
import heapq

from redis.asyncio import Redis
from validator.db.src.database import PSQLDB
from validator.control_node.src.control_config import Config
from validator.models import Contender
from core.tasks import Task
from core import tasks_config as tcfg
from validator.utils import contender_utils as putils
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TaskScheduleInfo:
    task: Task
    total_requests: int
    interval: float
    next_schedule_time: float
    remaining_requests: int

    def __lt__(self, other: "TaskScheduleInfo"):
        return self.next_schedule_time < other.next_schedule_time


async def _load_contenders(psql_db: PSQLDB) -> List[Contender]:
    return await putils.load_contenders(psql_db)


async def _group_contenders_by_task(contenders: List[Contender]) -> Dict[Task, List[Contender]]:
    task_groups: Dict[Task, List[Contender]] = {}
    for contender in contenders:
        if contender.task not in Task._value2member_map_:
            continue
        task = Task(contender.task)
        if task not in task_groups:
            task_groups[task] = []
        task_groups[task].append(contender)
    return task_groups


def _calculate_task_requests(task: Task, contenders: List[Contender]) -> int:
    config = tcfg.TASK_TO_CONFIG[task]
    total_capacity = sum(c.capacity_to_score for c in contenders)
    return int(total_capacity / config.volume_to_requests_conversion)


async def _initialize_task_schedules(task_groups: Dict[Task, List[Contender]]) -> List[TaskScheduleInfo]:
    schedules = []
    current_time = time.time()
    for task, contenders in task_groups.items():
        total_requests = _calculate_task_requests(task, contenders)
        interval = 3600 / total_requests if total_requests > 0 else 3600
        schedule = TaskScheduleInfo(
            task=task,
            total_requests=total_requests,
            interval=interval,
            next_schedule_time=current_time,
            remaining_requests=total_requests,
        )
        heapq.heappush(schedules, schedule)
    return schedules


async def _update_redis_remaining_requests(redis_db: Redis, task: Task, remaining_requests: int):
    key = f"task_synthetics_info:{task.value}:requests_remaining"
    await redis_db.set(key, remaining_requests)


async def _get_redis_remaining_requests(redis_db: Redis, task: Task) -> int:
    key = f"task_synthetics_info:{task.value}:requests_remaining"
    value = await redis_db.get(key)
    return int(value) if value is not None else 0


async def _schedule_synthetic_query(redis_db: Redis, task: Task, max_len: int):
    await putils.add_synthetic_query_to_queue(redis_db, task, max_len)


async def schedule_synthetics_until_done(config: Config):
    contenders = await _load_contenders(config.psql_db)
    task_groups = await _group_contenders_by_task(contenders)
    task_schedules = await _initialize_task_schedules(task_groups)

    logger.debug(f"Contenders: {contenders}, schedules: {task_schedules}, ")

    for schedule in task_schedules:
        await _update_redis_remaining_requests(config.redis_db, schedule.task, schedule.total_requests)

    while task_schedules:
        schedule = heapq.heappop(task_schedules)
        current_time = time.time()
        time_to_sleep = schedule.next_schedule_time - current_time

        if time_to_sleep > 0:
            logger.info(f"Sleeping for {time_to_sleep:.2f} seconds")
            sleep_chunk = 2  # Sleep in 2-second chunks to make debugging easier
            while time_to_sleep > 0:
                await asyncio.sleep(min(sleep_chunk, time_to_sleep))
                time_to_sleep -= sleep_chunk

        latest_remaining_requests = await _get_redis_remaining_requests(config.redis_db, schedule.task)
        requests_to_skip = schedule.remaining_requests - latest_remaining_requests

        if requests_to_skip > 0:
            logger.info(f"Skipping {requests_to_skip} requests for task {schedule.task}")
            schedule.next_schedule_time += schedule.interval * requests_to_skip

        if latest_remaining_requests > 0:
            await _schedule_synthetic_query(config.redis_db, schedule.task, max_len=100)
            logger.debug(
                f"latest_remaining_requests: {latest_remaining_requests}, next schedule time: {datetime.datetime.fromtimestamp(schedule.next_schedule_time)}"
            )
            remaining_requests = latest_remaining_requests - 1
            await _update_redis_remaining_requests(config.redis_db, schedule.task, remaining_requests)
            schedule.next_schedule_time = current_time + schedule.interval
            schedule.remaining_requests = remaining_requests
            logger.debug(f"Scheduled synthetic query for task {schedule.task}. Remaining: {remaining_requests}")

        if remaining_requests > 0:
            heapq.heappush(task_schedules, schedule)
        else:
            logger.info(f"No more requests remaining for task {schedule.task}")

    logger.info("All tasks completed")
