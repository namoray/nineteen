import asyncio
import base64
import random
import threading
import httpx
from typing import Dict, Any

from pydantic import BaseModel
from core import Task, tasks
import bittensor as bt
from models import base_models, utility_models
from core import utils as cutils
from PIL.Image import Image
from redis.asyncio import Redis
from validator.utils import redis_constants as cst
from validator.utils import redis_utils as rutils, synthetic_utils as sutils, query_utils as qutils
from core.logging import get_logger

logger = get_logger(__name__)

SEED = "seed"
TEMPERATURE = "temperature"
TEXT_PROMPTS = "text_prompts"


def load_postie_to_pil(image_path: str) -> Image:
    with open(image_path, "rb") as image_file:
        base64_string = base64.b64encode(image_file.read()).decode("utf-8")
    pil_image = cutils.base64_to_pil(base64_string)
    return pil_image


my_boy_postie = load_postie_to_pil("validation/synthetic_data/postie.png")


def _my_boy_postie() -> str:
    b64_postie_altered = qutils.alter_image(my_boy_postie)
    return b64_postie_altered


# TOOD: Change to mapping
async def _store_synthetic_data_in_redis(redis_db: Redis, task: Task, synthetic_data: BaseModel) -> None:
    synthetic_data_json = await rutils.json_load_from_redis(redis_db, cst.SYNTHETIC_DATA_KEY)
    synthetic_data_json[task] = synthetic_data
    await rutils.save_json_to_redis(redis_db, cst.SYNTHETIC_DATA_KEY, synthetic_data_json)


async def _update_synthetic_data_for_task(redis_db: Redis, task: Task, external_server_url: str) -> Dict[str, Any]:
    if task == Task.avatar:
        synthetic_data = base_models.AvatarIncoming(
            seed=random.randint(1, 1_000_000_000),
            text_prompts=[sutils.get_random_avatar_text_prompt()],
            height=1280,
            width=1280,
            steps=15,
            control_strength=0.5,
            ipadapter_strength=0.5,
            init_image=_my_boy_postie(),
        ).dict()
        await _store_synthetic_data_in_redis(redis_db, task, synthetic_data)
    else:
        try:
            async with httpx.AsyncClient(timeout=7) as client:
                response = await client.post(
                    external_server_url + "get-synthetic-data",
                    json={"task": task.value},
                )
                response.raise_for_status()  # raises an HTTPError if an unsuccessful status code was received
        except httpx.RequestError:
            # bt.logging.warning(f"Getting synthetic data error: {err.request.url!r}: {err}")
            return None
        except httpx.HTTPStatusError:
            # bt.logging.warning(
            #     f"Syntehtic data error; status code {err.response.status_code} while requesting {err.request.url!r}: {err}"
            # )
            return None

        try:
            response_json = response.json()
        except ValueError as e:
            bt.logging.error(f"Synthetic data Response contained invalid JSON: error :{e}")
            return None

        await _store_synthetic_data_in_redis(redis_db, task, response_json)


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
            target=cutils.start_async_loop, args=_continuously_fetch_synthetic_data_for_tasks, daemon=True
        )
        self.thread.start()


## Testing utils
async def patched_update_synthetic_data(redis_db: Redis, task: Task = Task.chat_llama_3):
    synthetic_data = base_models.ChatIncoming(
        seed=random.randint(1, 1_000_000_000),
        temperature=0.5,
        messages=[utility_models.Message(role=utility_models.Role.user, content="Test content prompt")],
        model=utility_models.ChatModels.llama_3,
    ).model_dump()

    await _store_synthetic_data_in_redis(redis_db, Task.chat_llama_3, synthetic_data)

    logger.info(f"Stored synthetic data for task: {task.value}!")


if __name__ == "__main__":
    import time

    redis_db = Redis()
    synthetic_data_manager = SyntheticDataManager(redis_db, "", start_event_loop=False)
    _update_synthetic_data_for_task = patched_update_synthetic_data
    synthetic_data_manager._start_synthetic_event_loop()

    while True:
        time.sleep(100)
