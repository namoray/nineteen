import asyncio
import random
import sys

from models import base_models, utility_models
from validator.utils import (
    synthetic_utils as sutils,
    synthetic_constants as scst,
    generic_utils as gutils,
)
from core import Task, dataclasses as dc, tasks_config

import markovify
import datasets
import diskcache
from functools import lru_cache
from core.logging import get_logger

logger = get_logger(__name__)


# NOTE: any danger here of massively gorwing cache?
@lru_cache(maxsize=1)
def get_cached_markov_model():
    logger.info("Loading markov model from caption_data...")
    dataset = datasets.load_dataset("caption_data/data")
    text = [i["query"] for i in dataset["train"]]
    return markovify.Text(" ".join(text))


# Async wrapper to use the cached model
async def markov_model_factory():
    return await asyncio.to_thread(get_cached_markov_model)


@lru_cache(maxsize=1)
def image_cache_factory() -> diskcache.Cache:
    cache = diskcache.Cache("./image_cache")
    return cache


async def _get_markov_sentence(max_words: int = 10) -> str:
    markov_text_generation_model = await markov_model_factory()
    text = None
    while text is None:
        text = markov_text_generation_model.make_sentence(max_words=max_words)
    return text


async def generate_chat_synthetic(model: str) -> base_models.ChatIncoming:
    user_content = await _get_markov_sentence(max_words=80)
    messages = [utility_models.Message(content=user_content, role=utility_models.Role.user.value)]

    if random.random() < 0.1:
        messages.append(
            utility_models.Message(
                content=await _get_markov_sentence(max_words=80),
                role=utility_models.Role.assistant.value,
            )
        )
        messages.append(
            utility_models.Message(
                content=await _get_markov_sentence(max_words=80),
                role=utility_models.Role.user.value,
            )
        )
    return base_models.ChatIncoming(
        messages=messages,
        top_p=1,
        seed=random.randint(1, scst.MAX_SEED),
        temperature=round(random.random(), 1),
        max_tokens=1024,
        model=model,
    )


async def generate_text_to_image_synthetic(
    engine: str,
) -> base_models.TextToImageIncoming:
    positive_text = await _get_markov_sentence(max_words=20)
    text_prompts = [dc.TextPrompt(text=positive_text, weight=1.0)]
    seed = random.randint(1, scst.MAX_SEED)

    if engine == utility_models.EngineEnum.PLAYGROUND.value:
        height = 1024
        width = 1024
        cfg_scale = 4.0
        steps = 30
    elif engine == utility_models.EngineEnum.PROTEUS.value:
        height = 1280
        width = 1280
        cfg_scale = 2.0
        steps = 8
    elif engine == utility_models.EngineEnum.DREAMSHAPER.value:
        height = 1024
        width = 1024
        cfg_scale = 3.5
        steps = 8
    else:
        raise ValueError(f"Engine {engine} not supported")

    return base_models.TextToImageIncoming(
        text_prompts=text_prompts,
        seed=seed,
        engine=engine,
        height=height,
        width=width,
        cfg_scale=cfg_scale,
        steps=steps,
    )


async def generate_image_to_image_synthetic(
    engine: str,
) -> base_models.ImageToImageIncoming:
    cache = image_cache_factory()

    positive_text = await _get_markov_sentence(max_words=20)
    text_prompts = [dc.TextPrompt(text=positive_text, weight=1.0)]
    seed = random.randint(1, scst.MAX_SEED)

    if engine == utility_models.EngineEnum.PLAYGROUND.value:
        height = 1024
        width = 1024
        cfg_scale = 4.0
        steps = 30
        image_strength = 0.5
    elif engine == utility_models.EngineEnum.PROTEUS.value:
        height = 1280
        width = 1280
        cfg_scale = 2.0
        steps = 8
        image_strength = 0.5
    elif engine == utility_models.EngineEnum.DREAMSHAPER.value:
        height = 1024
        width = 1024
        cfg_scale = 3.5
        steps = 8
        image_strength = 0.5
    else:
        raise ValueError(f"Engine {engine} not supported")

    init_image = await sutils.get_random_image_b64(cache)

    return base_models.ImageToImageIncoming(
        init_image=init_image,
        image_strength=image_strength,
        text_prompts=text_prompts,
        seed=seed,
        engine=engine,
        height=height,
        width=width,
        cfg_scale=cfg_scale,
        steps=steps,
    )


async def generate_inpaint_synthetic() -> base_models.InpaintIncoming:
    cache = image_cache_factory()
    positive_text = await _get_markov_sentence(max_words=20)
    text_prompts = [dc.TextPrompt(text=positive_text, weight=1.0)]
    seed = random.randint(1, scst.MAX_SEED)

    init_image = await sutils.get_random_image_b64(cache)
    mask_image = sutils.generate_mask_with_circle(init_image)

    return base_models.InpaintIncoming(
        text_prompts=text_prompts,
        init_image=init_image,
        ipadapter_strength=0.5,
        control_strength=0.5,
        seed=seed,
        mask_image=mask_image,
        height=1016,
        width=1016,
        steps=8,
    )


async def generate_avatar_synthetic() -> base_models.AvatarIncoming:
    positive_text = await _get_markov_sentence(max_words=20)
    text_prompts = [dc.TextPrompt(text=positive_text, weight=1.0)]
    seed = random.randint(1, scst.MAX_SEED)

    init_image = sutils.get_randomly_edited_face_picture_for_avatar()

    return base_models.AvatarIncoming(
        init_image=init_image,
        text_prompts=text_prompts,
        ipadapter_strength=0.5,
        control_strength=0.5,
        height=1280,
        width=1280,
        seed=seed,
        steps=8,
    )


async def generate_synthetic_data(task: Task) -> None:
    """
    Gets task config and dynamically calls the synthetic generation function
    Not super clean, but it works
    """
    task_config = tasks_config.TASK_TO_CONFIG[task]
    generative_function_name = task_config.synthetic_generation_config.func

    if generative_function_name not in sys.modules[__name__].__dict__:
        raise ValueError(
            f"Function {generative_function_name} not found in generate_synthetic_data, some config is wrong"
        )

    with gutils.log_time(f"Generating synthetic data for {task}", logger):
        func = getattr(sys.modules[__name__], generative_function_name)
        kwargs = task_config.synthetic_generation_config.kwargs

        return await func(**kwargs)


# async def generate_clip_synthetic() -> base_models.ClipEmbeddingsIncoming:
#     init_image = await sutils.get_random_image_b64(cache)

#     if init_image is None:
#         raise ValueError("No images found")

#     return base_models.ClipEmbeddingsIncoming(
#         image_b64s=[init_image],
#     )


# async def generate_upscale_synthetic() -> base_models.UpscaleIncoming:
#     init_image = await sutils.get_random_image_b64(cache)
#     init_image = sutils.resize_image(init_image)

#     return base_models.UpscaleIncoming(
#         image=init_image,
#     )
