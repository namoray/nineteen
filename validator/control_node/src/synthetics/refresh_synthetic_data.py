import asyncio
import datetime
import json
import time
from pydantic import BaseModel
from core.tasks import Task
from redis.asyncio import Redis
from validator.utils import (
    synthetic_utils as sutils,
    redis_constants as rcst,
    synthetic_constants as scst,
)
from validator.control_node.src.synthetics import synthetic_generation_funcs
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


async def update_tasks_synthetic_data(redis_db: Redis, slow_sync: bool = True, task: Task | None = None) -> None:
    if task is not None:
        now = datetime.datetime.now().timestamp()
        synthetic_data_version = await sutils.get_synthetic_data_version(redis_db, task)
        if synthetic_data_version is None or now - synthetic_data_version > scst.SYNTHETIC_DATA_EXPIRATION_TIME:
            new_synthetic_data = await synthetic_generation_funcs.generate_synthetic_data(task)
            await _store_synthetic_data_in_redis(redis_db, task, new_synthetic_data)

    else:
        for task in Task:
            now = datetime.datetime.now().timestamp()
            synthetic_data_version = await sutils.get_synthetic_data_version(redis_db, task)
            if synthetic_data_version is None or now - synthetic_data_version > scst.SYNTHETIC_DATA_EXPIRATION_TIME:
                new_synthetic_data = await synthetic_generation_funcs.generate_synthetic_data(task)
                await _store_synthetic_data_in_redis(redis_db, task, new_synthetic_data)
            if slow_sync:
                await asyncio.sleep(0.1)


async def continuously_fetch_synthetic_data_for_tasks(redis_db: Redis) -> None:
    await update_tasks_synthetic_data(redis_db, slow_sync=False)

    while True:
        await update_tasks_synthetic_data(redis_db, slow_sync=True)

    
async def main():
    redis_db = Redis(host="redis", db=0)
    await continuously_fetch_synthetic_data_for_tasks(redis_db)


if __name__ == "__main__":
    asyncio.run(main())
