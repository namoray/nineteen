import asyncio
import random
import threading
from flask import json

from pydantic import BaseModel
from core import Task, tasks
from models import base_models, utility_models
from core import utils as cutils
from redis.asyncio import Redis
from validator.utils import redis_constants as cst
from validator.utils import (
    redis_utils as rutils,
    synthetic_utils as sutils,
    redis_constants as rcst,
)
from core.logging import get_logger

logger = get_logger(__name__)


# TOOD: Change to mapping
async def _store_synthetic_data_in_redis(redis_db: Redis, task: Task, synthetic_data: BaseModel) -> None:
    pipe = redis_db.pipeline(transaction=True)

    task_key = sutils.construct_synthetic_data_task_key(task)
    await pipe.set(task_key, json.dumps(synthetic_data.model_dump()))

    current_time = int(time.time() * 1000) / 1000
    await pipe.hset(rcst.SYNTHETIC_DATA_VERSIONS_KEY, task.value, current_time)

    await pipe.execute()


async def _continuously_fetch_synthetic_data_for_tasks(redis_db: Redis, external_server_url: str) -> None:
    tasks_needing_synthetic_data = [
        task for task in tasks.Task if task not in await get_stored_synthetic_data(redis_db)
    ]
    while tasks_needing_synthetic_data:
        sync_tasks = []
        for task in tasks_needing_synthetic_data:
            sync_tasks.append(asyncio.create_task(_update_synthetic_data_for_task(redis_db, task, external_server_url)))

        await asyncio.gather(*sync_tasks)
        tasks_needing_synthetic_data = [
            task for task in tasks.Task if task not in await get_stored_synthetic_data(redis_db)
        ]

    while True:
        for task in tasks.Task:
            await _update_synthetic_data_for_task(redis_db, task, external_server_url)
            await asyncio.sleep(3)


async def get_stored_synthetic_data(redis_db: Redis):
    return await rutils.json_load_from_redis(redis_db, cst.SYNTHETIC_DATA_KEY)


class SyntheticDataManager:
    def __init__(self, redis_db: Redis, external_server_url: str, start_event_loop: bool = True) -> None:
        self.redis_db = redis_db
        self.external_server_url = external_server_url
        if start_event_loop:
            self._start_synthetic_event_loop()

    def _start_synthetic_event_loop(self):
        self.thread = threading.Thread(
            target=cutils.start_async_loop,
            args=(_continuously_fetch_synthetic_data_for_tasks, self.redis_db, self.external_server_url),
            daemon=True,
        )
        self.thread.start()


## Testing utils
async def patched_update_synthetic_data(
    redis_db: Redis, task: Task = Task.chat_llama_3, external_server_url: str = ""
) -> None:
    synthetic_data = base_models.ChatIncoming(
        seed=random.randint(1, 1_000_000_000),
        temperature=0.5,
        messages=[utility_models.Message(role=utility_models.Role.user, content="Test content prompt")],
        model=utility_models.ChatModels.llama_3,
    )

    await _store_synthetic_data_in_redis(redis_db, Task.chat_llama_3, synthetic_data)

    logger.debug(f"Stored synthetic data for task: {task.value}!")


if __name__ == "__main__":
    import time

    redis_db = Redis(host="redis", db=0)
    synthetic_data_manager = SyntheticDataManager(redis_db, "", start_event_loop=False)
    _update_synthetic_data_for_task = patched_update_synthetic_data
    synthetic_data_manager._start_synthetic_event_loop()

    while True:
        time.sleep(100)
