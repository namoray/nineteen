import random
import string
from typing import Dict, Any

from core import Task, tasks
from models import base_models
from vali_new.utils import redis_utils as rutils, redis_constants as rcst, query_utils as qutils
from core import dataclasses as dc
from redis.asyncio import Redis

SEED = "seed"
TEMPERATURE = "temperature"
TEXT_PROMPTS = "text_prompts"


def _get_random_letters(length: int) -> str:
    letters = string.ascii_letters
    return "".join(random.choice(letters) for i in range(length))


def get_random_text_prompt() -> dc.TextPrompt:
    nouns = ['king', 'man', 'woman', 'joker', 'queen', 'child', 'doctor', 'teacher', 'soldier', 'merchant']  # fmt: off
    locations = ['forest', 'castle', 'city', 'village', 'desert', 'oceanside', 'mountain', 'garden', 'library', 'market']  # fmt: off
    looks = ['happy', 'sad', 'angry', 'worried', 'curious', 'lost', 'busy', 'relaxed', 'fearful', 'thoughtful']  # fmt: off
    actions = ['running', 'walking', 'reading', 'talking', 'sleeping', 'dancing', 'working', 'playing', 'watching', 'singing']  # fmt: off
    times = ['in the morning', 'at noon', 'in the afternoon', 'in the evening', 'at night', 'at midnight', 'at dawn', 'at dusk', 'during a storm', 'during a festival']  # fmt: off

    noun = random.choice(nouns)
    location = random.choice(locations)
    look = random.choice(looks)
    action = random.choice(actions)
    time = random.choice(times)

    text = f"{noun} in a {location}, looking {look}, {action} {time}"
    return dc.TextPrompt(text=text, weight=1.0)


async def fetch_synthetic_data_for_task(redis_db: Redis, task: Task) -> Dict[str, Any]:
    # TODO: replace with redisJSON stuff
    all_synthetic_data = await rutils.json_load_from_redis(redis_db, key=rcst.SYNTHETIC_DATA_KEY)
    assert (
        task in all_synthetic_data
    ), f"Somehow the task is not in synthetic data? task: {task}, synthetic_data: {all_synthetic_data}"

    synth_data = all_synthetic_data[task]
    task_config = tasks.get_task_config(task)
    if task_config.task_type == tasks.TaskType.IMAGE:
        synth_data[SEED] = random.randint(1, 1_000_000_000)
        synth_data[TEXT_PROMPTS] = get_random_text_prompt()
    elif task_config.task_type == tasks.TaskType.TEXT:
        synth_data[SEED] = random.randint(1, 1_000_000_000)
        synth_data[TEMPERATURE] = round(random.uniform(0, 1), 2)
    elif task_config.task_type == tasks.TaskType.CLIP:
        synth_model = base_models.ClipEmbeddingsIncoming(**synth_data)
        synth_model_altered = qutils.alter_clip_body(synth_model)
        synth_data = synth_model_altered.dict()

    return synth_data
