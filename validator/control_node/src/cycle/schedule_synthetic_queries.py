import asyncio
from dataclasses import dataclass
import json
import random
import time
from typing import Dict, List, Any
import heapq

from redis.asyncio import Redis
from validator.db.src.database import PSQLDB
from validator.control_node.src.control_config import Config
from validator.models import Contender
from core import task_config as tcfg
from validator.utils.contender import contender_utils as putils
from validator.utils.generic import generic_constants as gcst
from validator.utils.redis import redis_constants as rcst
from core import constants as ccst
from fiber.logging_utils import get_logger

from validator.utils.synthetic.synthetic_utils import (
    get_random_image_b64,
    get_synthetic_data_version,
    construct_synthetic_data_task_key,
    fetch_synthetic_data_for_task,
)

from validator.control_node.src.synthetics.synthetic_generation_funcs import (
    generate_chat_synthetic,
    generate_text_to_image_synthetic,
)

logger = get_logger(__name__)


@dataclass(order=True)
class TaskScheduleInfo:
    next_schedule_time: float
    task: str
    total_requests: int
    interval: float
    remaining_requests: int

    def __post_init__(self):
        # Ensure heapq uses next_schedule_time for ordering
        object.__setattr__(self, "sort_index", self.next_schedule_time)


async def _load_contenders(psql_db: PSQLDB) -> List[Contender]:
    return await putils.load_contenders(psql_db)


async def _group_contenders_by_task(contenders: List[Contender]) -> Dict[str, List[Contender]]:
    task_groups: Dict[str, List[Contender]] = {}
    task_configs = tcfg.get_task_configs()
    for contender in contenders:
        if contender.task not in task_configs:
            continue
        if contender.task not in task_groups:
            task_groups[contender.task] = []
        task_groups[contender.task].append(contender)
    return task_groups


def _calculate_task_requests(task: str, contenders: List[Contender], config: Config) -> int:
    task_config = tcfg.get_enabled_task_config(task)
    if task_config is None:
        return 0
    total_capacity = sum(c.capacity_to_score for c in contenders) * config.scoring_period_time_multiplier
    return int(total_capacity / task_config.volume_to_requests_conversion)


def _get_initial_schedule_time(current_time: float, interval: float) -> float:
    return current_time + random.uniform(0, interval)


async def _initialize_task_schedules(task_groups: Dict[str, List[Contender]], config: Config) -> List[TaskScheduleInfo]:
    scoring_period_time = ccst.SCORING_PERIOD_TIME * config.scoring_period_time_multiplier
    schedules = []
    for task, contenders in task_groups.items():
        total_requests = _calculate_task_requests(task, contenders, config)
        if total_requests > 0:
            interval = scoring_period_time / (total_requests + 1)
            current_time = time.time()
            first_schedule_time = _get_initial_schedule_time(current_time, interval)
            schedule = TaskScheduleInfo(
                task=task,
                total_requests=total_requests,
                interval=interval,
                next_schedule_time=first_schedule_time,
                remaining_requests=total_requests,
            )
            heapq.heappush(schedules, schedule)
    return schedules


async def _update_redis_remaining_requests(redis_db: Redis, task: str, remaining_requests: int):
    key = f"task_synthetics_info:{task}:requests_remaining"
    await redis_db.set(key, remaining_requests)


async def _get_redis_remaining_requests(redis_db: Redis, task: str) -> int:
    key = f"task_synthetics_info:{task}:requests_remaining"
    value = await redis_db.get(key)
    return int(value) if value is not None else 0


async def _schedule_synthetic_query(redis_db: Redis, task: str, max_len: int):
    try:
        synthetic_data = await fetch_synthetic_data_for_task(redis_db, task)
    except ValueError as e:
        logger.error(f"Failed to fetch synthetic data for task {task}: {e}")
        return

    await redis_db.rpush(rcst.QUERY_QUEUE_KEY, json.dumps(synthetic_data))  # type: ignore


async def _clear_old_synthetic_queries(redis_db: Redis):
    all_items = await redis_db.lrange(rcst.QUERY_QUEUE_KEY, 0, -1)  # type: ignore

    non_synthetic_items = [item for item in all_items if json.loads(item).get("task_type") != gcst.SYNTHETIC]
    await redis_db.delete(rcst.QUERY_QUEUE_KEY)

    if non_synthetic_items:
        await redis_db.rpush(rcst.QUERY_QUEUE_KEY, *non_synthetic_items)  # type: ignore

    logger.info(f"Cleared {len(all_items) - len(non_synthetic_items)} synthetic queries from the queue")


async def _fetch_tasks_in_chunks(redis_client: Redis, batch_size: int) -> List[Dict[str, Any]]:
    tasks = []

    for _ in range(batch_size):
        task_raw = await redis_client.lpop(rcst.CONTROL_NODE_QUEUE_KEY)  # type: ignore
        if task_raw:
            try:
                task_data = json.loads(task_raw)
                tasks.append(task_data)
            except Exception as e:
                logger.error(f"Failed to parse task from Redis queue: {str(e)}")
        else:
            break

    return tasks


async def _enhance_task(task_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        logger.info(f"Processing task {task_data['id']} of type {task_data['task_type']}...")

        # Generate synthetic payload according to task type
        if task_data["task_type"] == "chat":
            synthetic_payload = await generate_chat_synthetic(model=task_data["model"])
            task_data["synthetic_payload"] = synthetic_payload.dict()
        elif task_data["task_type"] == "text-to-image":
            synthetic_payload = await generate_text_to_image_synthetic(model=task_data["model"])
            task_data["synthetic_payload"] = synthetic_payload.dict()
        else:
            raise ValueError(f"Unknown task type {task_data['task_type']}")

        # Mark task as enhanced and add the timestamp
        task_data["status"] = "enhanced"
        task_data["enhanced_at"] = time.time()

        return task_data

    except Exception as e:
        logger.error(f"Failed to enhance task {task_data.get('id', 'unknown')}: {str(e)}")
        return task_data


async def _push_to_query_node(redis_client: Redis, task_data: Dict[str, Any]):
    try:
        await redis_client.rpush(rcst.QUERY_QUEUE_KEY, json.dumps(task_data))  # type: ignore
        logger.info(f"Task {task_data['id']} has been successfully enhanced and queued for the Query Node!")

    except Exception as e:
        logger.error(f"Failed to queue enhanced task {task_data.get('id', 'unknown')} to Query Node: {str(e)}")


async def warmup_function(config: Config):
    logger.info("Loading shared resources for warmup.")

    warmup_tasks = [
        {"id": "warmup-chat-task", "task_type": "chat", "model": "default-model"},
        {"id": "warmup-text-to-image-task", "task_type": "text-to-image", "model": "default-model"},
        {"id": "warmup-image-to-image-task", "task_type": "image-to-image", "model": "default-model"},
    ]

    for task_data in warmup_tasks:
        try:
            logger.info(f"Warming up by enhancing task {task_data['id']}...")

            enhanced_task = await _enhance_task(task_data)

            await _push_to_query_node(config.redis_db, enhanced_task)

            logger.info(f"Warmup task {task_data['id']} has been successfully enhanced and queued for the Query Node.")

        except Exception as e:
            logger.error(f"Error during warmup processing for task {task_data['id']}: {e}")

    logger.info("Warmup completed. Entering the main control loop.")


async def schedule_synthetics_until_done(config: Config):
    redis_client = config.redis_db

    while True:
        tasks = await _fetch_tasks_in_chunks(redis_client, rcst.CONTROL_TASK_CHUNK_SIZE)

        if not tasks:
            logger.info("No more tasks to fetch, exiting the scheduling loop.")
            break

        logger.info(f"Fetched {len(tasks)} tasks from Redis.")

        enhanced_tasks = await asyncio.gather(*[_enhance_task(task) for task in tasks])

        await asyncio.gather(*[_push_to_query_node(redis_client, task) for task in enhanced_tasks])

        logger.info(f"Batch of {len(tasks)} tasks has been enhanced and passed to the Query Node.")
