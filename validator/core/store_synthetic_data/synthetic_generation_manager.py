import asyncio
import datetime
import threading
from flask import json
import time
from pydantic import BaseModel
from core import Task
from core import utils as cutils
from redis.asyncio import Redis
from validator.utils import (
    synthetic_utils as sutils,
    redis_constants as rcst,
    synthetic_constants as scst,
)
from validator.core.store_synthetic_data import generate_synthetic_data
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


async def update_tasks_synthetic_data(redis_db: Redis, slow_sync: bool = True) -> None:
    for task in Task:
        now = datetime.datetime.now().timestamp()
        synthetic_data_version = await sutils.get_synthetic_data_version(redis_db, task)
        if synthetic_data_version is None or now - synthetic_data_version > scst.SYNTHETIC_DATA_EXPIRATION_TIME:
            new_synthetic_data = await generate_synthetic_data.generate_synthetic_data(task)
            await _store_synthetic_data_in_redis(redis_db, task, new_synthetic_data)
        if slow_sync:
            await asyncio.sleep(0.1)


async def _continuously_fetch_synthetic_data_for_tasks(redis_db: Redis) -> None:
    await update_tasks_synthetic_data(redis_db, slow_sync=False)

    while True:
        await update_tasks_synthetic_data(redis_db, slow_sync=True)


class SyntheticDataManager:
    def __init__(self, redis_db: Redis, start_event_loop: bool = True) -> None:
        self.redis_db = redis_db
        if start_event_loop:
            self._start_synthetic_event_loop()

    def _start_synthetic_event_loop(self):
        self.thread = threading.Thread(
            target=cutils.start_async_loop,
            args=(_continuously_fetch_synthetic_data_for_tasks, self.redis_db),
            daemon=True,
        )
        self.thread.start()


if __name__ == "__main__":
    import time

    redis_db = Redis(host="redis", db=0)
    synthetic_data_manager = SyntheticDataManager(redis_db, start_event_loop=False)
    synthetic_data_manager._start_synthetic_event_loop()

    while True:
        time.sleep(100)
