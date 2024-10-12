import asyncio
import json
import time
from pydantic import BaseModel
from core import task_config as tcfg
from redis.asyncio import Redis
from typing import List
from validator.control_node.src.control_config import Config
from validator.utils.redis import redis_constants as rcst
from validator.utils.synthetic.synthetic_utils import (
    construct_synthetic_data_task_key,
    fetch_synthetic_data_for_task,
)
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


async def _store_synthetic_data_in_redis(redis_db: Redis, task: str, synthetic_data: BaseModel) -> None:
    pipe = redis_db.pipeline(transaction=True)

    task_key = construct_synthetic_data_task_key(task)
    await pipe.set(task_key, json.dumps(synthetic_data.model_dump()))

    current_time = int(time.time())
    await pipe.hset(rcst.SYNTHETIC_DATA_VERSIONS_KEY, task, current_time)  # type: ignore

    await pipe.execute()


async def warm_up_synthetic_cache(redis_db: Redis, config: Config, tasks: List[str]):
    """
    Preloads synthetic data for all enabled tasks into Redis.
    """
    for task in tasks:
        task_config = tcfg.get_enabled_task_config(task)
        if task_config is None:
            logger.warning(f"Task configuration for '{task}' not found. Skipping cache warm-up.")
            continue

        try:
            synthetic_data = await fetch_synthetic_data_for_task(redis_db, task)
            synthetic_data_model = BaseModel.parse_obj(synthetic_data)
            await _store_synthetic_data_in_redis(redis_db, task, synthetic_data_model)
            logger.info(f"Preloaded synthetic data for task '{task}'.")
        except Exception as e:
            logger.error(f"Failed to preload synthetic data for task '{task}': {e}")

    logger.info("Synthetic cache warm-up completed.")


async def main(config: Config):
    """
    Handles initial cache warm-up.
    """
    tasks = [task for task in tcfg.get_task_configs() if tcfg.get_enabled_task_config(task)]
    await warm_up_synthetic_cache(config.redis_db, config, tasks)


if __name__ == "__main__":
    import asyncio
    from validator.control_node.src.control_config import load_config

    config = load_config()
    asyncio.run(main(config))
