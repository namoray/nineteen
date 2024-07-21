import random
from typing import Any

from core import Task, tasks_config
from models import base_models
from validator.utils import (
    redis_utils as rutils,
    redis_constants as rcst,
    query_utils as qutils,
    synthetic_constants as scst,
)
from core import dataclasses as dc
from redis.asyncio import Redis
from models import synapses
from core import bittensor_overrides as bt
import base64
from io import BytesIO

import aiohttp
import diskcache
from PIL import Image
import uuid
import numpy as np
from core.logging import get_logger

logger = get_logger(__name__)


def get_randomly_edited_face_picture_for_avatar() -> str:
    """
    For avatar we need a face image.

    We must satisfy the criteria: image must not be cacheable

    As long as we satisfy that, we're good - since we score organic queries.

    Hence, we can use a single picture and just edit it to generate 2**(1024*1024) unique images
    """

    my_boy_postie = _load_postie_to_pil("validator/core/assets/postie.png")
    return _alter_my_boy_postie(my_boy_postie)


def _get_random_text_prompt() -> dc.TextPrompt:
    nouns = ["king", "man", "woman", "joker", "queen", "child", "doctor", "teacher", "soldier", "merchant"]  # fmt: off
    locations = [
        "forest",
        "castle",
        "city",
        "village",
        "desert",
        "oceanside",
        "mountain",
        "garden",
        "library",
        "market",
    ]  # fmt: off
    looks = [
        "happy",
        "sad",
        "angry",
        "worried",
        "curious",
        "lost",
        "busy",
        "relaxed",
        "fearful",
        "thoughtful",
    ]  # fmt: off
    actions = [
        "running",
        "walking",
        "reading",
        "talking",
        "sleeping",
        "dancing",
        "working",
        "playing",
        "watching",
        "singing",
    ]  # fmt: off
    times = [
        "in the morning",
        "at noon",
        "in the afternoon",
        "in the evening",
        "at night",
        "at midnight",
        "at dawn",
        "at dusk",
        "during a storm",
        "during a festival",
    ]  # fmt: off

    noun = random.choice(nouns)
    location = random.choice(locations)
    look = random.choice(looks)
    action = random.choice(actions)
    time = random.choice(times)

    text = f"{noun} in a {location}, looking {look}, {action} {time}"
    return dc.TextPrompt(text=text, weight=1.0)


async def _get_random_picsum_image(x_dim: int, y_dim: int) -> str:
    """
    Generate a random image with the specified dimensions, by calling unsplash api.

    Args:
        x_dim (int): The width of the image.
        y_dim (int): The height of the image.

    Returns:
        str: The base64 encoded representation of the generated image.
    """
    async with aiohttp.ClientSession() as session:
        url = f"https://picsum.photos/{x_dim}/{y_dim}"
        async with session.get(url) as resp:
            data = await resp.read()

    img = Image.open(BytesIO(data))
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode()

    return img_b64


def _load_postie_to_pil(image_path: str) -> Image:
    with open(image_path, "rb") as image_file:
        base64_string = base64.b64encode(image_file.read()).decode("utf-8")
    pil_image = qutils.base64_to_pil(base64_string)
    return pil_image


def _alter_my_boy_postie(my_boy_postie: Image) -> str:
    b64_postie_altered = qutils.alter_image(my_boy_postie)
    return b64_postie_altered


async def get_random_image_b64(cache: diskcache.Cache) -> str:
    for key in cache.iterkeys():
        image_b64: str = cache.get(key, None)
        if image_b64 is None:
            cache.delete(key)
            continue

        if random.random() < 0.01:
            cache.delete(key)
        return image_b64

    random_picsum_image = await _get_random_picsum_image(1024, 1024)
    cache.add(key=str(uuid.uuid4()), value=random_picsum_image)
    return random_picsum_image


def generate_mask_with_circle(image_b64: str) -> str:
    image = Image.open(BytesIO(base64.b64decode(image_b64)))

    height, width = image.size

    center_x = np.random.randint(0, width)
    center_y = np.random.randint(0, height)
    radius = np.random.randint(20, 100)

    y, x = np.ogrid[:height, :width]

    mask = ((x - center_x) ** 2 + (y - center_y) ** 2 <= radius**2).astype(np.uint8)

    mask_bytes = mask.tobytes()
    mask_b64 = base64.b64encode(mask_bytes).decode("utf-8")

    return mask_b64


def construct_synthetic_data_task_key(task: Task) -> str:
    return rcst.SYNTHETIC_DATA_KEY + ":" + task.value


async def get_synthetic_data_version(redis_db: Redis, task: Task) -> float | None:
    version = await redis_db.hget(rcst.SYNTHETIC_DATA_VERSIONS_KEY, task.value)
    if version is not None:
        return float(version.decode("utf-8"))
    return None


# Takes anywhere from 1ms to 10ms
async def fetch_synthetic_data_for_task(redis_db: Redis, task: Task) -> dict[str, Any]:
    synthetic_data = await rutils.json_load_from_redis(
        redis_db, key=construct_synthetic_data_task_key(task), default=None
    )
    if synthetic_data is None:
        raise ValueError(f"No synthetic data found for task: {task}")

    task_type = tasks_config.TASK_TO_CONFIG[task].scoring_config.task_type
    if task_type == tasks_config.TaskType.IMAGE:
        synthetic_data[scst.SEED] = random.randint(1, 1_000_000_000)
        synthetic_data[scst.TEXT_PROMPTS] = _get_random_text_prompt()
    elif task_type == tasks_config.TaskType.TEXT:
        synthetic_data[scst.SEED] = random.randint(1, 1_000_000_000)
        synthetic_data[scst.TEMPERATURE] = round(random.uniform(0, 1), 2)
    elif task_type == tasks_config.TaskType.CLIP:
        synth_model = base_models.ClipEmbeddingsIncoming(**synthetic_data)
        synth_model_altered = qutils.alter_clip_body(synth_model)
        synthetic_data = synth_model_altered.model_dump()
    else:
        raise ValueError(f"Unknown task type: {task_type}")

    return convert_synthetic_data_to_synapse(synthetic_data, task)


def convert_synthetic_data_to_synapse(synthetic_data: dict[str, Any], task: Task) -> bt.Synapse:
    # dynamically get synapse from models.synapses using the task
    synapse_name = tasks_config.TASK_TO_CONFIG[task].synapse

    synapse = getattr(synapses, synapse_name)
    logger.debug(f"Synapse name for task  {task} is {synapse_name}. synapse is: {synapse}.")
    return synapse(**synthetic_data)
