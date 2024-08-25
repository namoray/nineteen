import asyncio
import random
import sys

from core.models import utility_models
from validator.utils import (
    synthetic_constants as scst,
)
from core.tasks import Task
from core import tasks_config
from core.models import payload_models

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
    dataset = datasets.load_dataset("assets/caption_data/data")
    text = [i["query"] for i in dataset["train"]]
    return markovify.Text(" ".join(text))


# Async wrapper to use the cached model
async def markov_model_factory():
    return await asyncio.to_thread(get_cached_markov_model)


@lru_cache(maxsize=1)
def image_cache_factory() -> diskcache.Cache:
    cache = diskcache.Cache("./cache/image_cache")
    return cache


async def _get_markov_sentence(max_words: int = 10) -> str:
    markov_text_generation_model = await markov_model_factory()
    text = None
    while text is None:
        text = markov_text_generation_model.make_sentence(max_words=max_words)
    return text


async def generate_chat_synthetic(model: str) -> payload_models.ChatPayload:
    user_content = await _get_markov_sentence(max_words=140)
    messages = [utility_models.Message(content=user_content, role=utility_models.Role.user.value)]

    if random.random() < 0.1:
        messages.append(
            utility_models.Message(
                content=await _get_markov_sentence(max_words=140),
                role=utility_models.Role.assistant.value,
            )
        )
        messages.append(
            utility_models.Message(
                content=await _get_markov_sentence(max_words=140),
                role=utility_models.Role.user.value,
            )
        )
    return payload_models.ChatPayload(
        messages=messages,
        temperature=round(random.random(), 1),
        max_tokens=1024,
        seed=random.randint(1, scst.MAX_SEED),
        model=model,
        top_p=1,
    )


async def generate_text_to_image_synthetic(
    model: str,
) -> payload_models.TextToImageRequest:
    prompt = await _get_markov_sentence(max_words=20)
    negative_prompt = await _get_markov_sentence(max_words=20)
    seed = random.randint(1, scst.MAX_SEED)

    if model == Task.proteus_text_to_image.value:
        height = 1024
        width = 1024
        cfg_scale = 4.0
        steps = 10
    elif model == Task.dreamshaper_text_to_image.value:
        height = 1024
        width = 1024
        cfg_scale = 3.0
        steps = 10
    else:
        raise ValueError(f"Model {model} not supported")

    return payload_models.TextToImageRequest(
        prompt=prompt,
        negative_prompt=negative_prompt,
        seed=seed,
        height=height,
        width=width,
        cfg_scale=cfg_scale,
        steps=steps,
        model=model,
    )


# async def generate_image_to_image_synthetic(
#     model: str,
# ) -> base_models.ImageToImageIncoming:
#     cache = image_cache_factory()

#     positive_text = await _get_markov_sentence(max_words=20)
#     text_prompts = [dc.TextPrompt(text=positive_text, weight=1.0)]
#     seed = random.randint(1, scst.MAX_SEED)

#     if model == Task.PLAYGROUND.value:
#         height = 1024
#         width = 1024
#         cfg_scale = 4.0
#         steps = 30
#         image_strength = 0.5
#     elif model == Task.PROTEUS.value:
#         height = 1280
#         width = 1280
#         cfg_scale = 2.0
#         steps = 8
#         image_strength = 0.5
#     elif model == Task.DREAMSHAPER.value:
#         height = 1024
#         width = 1024
#         cfg_scale = 3.5
#         steps = 8
#         image_strength = 0.5
#     else:
#         raise ValueError(f"Engine {model} not supported")

#     init_image = await sutils.get_random_image_b64(cache)

#     return base_models.ImageToImageIncoming(
#         init_image=init_image,
#         image_strength=image_strength,
#         text_prompts=text_prompts,
#         seed=seed,
#         model=model,
#         height=height,
#         width=width,
#         cfg_scale=cfg_scale,
#         steps=steps,
#     )


# async def generate_inpaint_synthetic() -> base_models.InpaintIncoming:
#     cache = image_cache_factory()
#     positive_text = await _get_markov_sentence(max_words=20)
#     text_prompts = [dc.TextPrompt(text=positive_text, weight=1.0)]
#     seed = random.randint(1, scst.MAX_SEED)

#     init_image = await sutils.get_random_image_b64(cache)
#     mask_image = sutils.generate_mask_with_circle(init_image)

#     return base_models.InpaintIncoming(
#         text_prompts=text_prompts,
#         init_image=init_image,
#         ipadapter_strength=0.5,
#         control_strength=0.5,
#         seed=seed,
#         mask_image=mask_image,
#         height=1016,
#         width=1016,
#         steps=8,
#     )


# async def generate_avatar_synthetic() -> base_models.AvatarIncoming:
#     positive_text = await _get_markov_sentence(max_words=20)
#     text_prompts = [dc.TextPrompt(text=positive_text, weight=1.0)]
#     seed = random.randint(1, scst.MAX_SEED)

#     init_image = sutils.get_randomly_edited_face_picture_for_avatar()

#     return base_models.AvatarIncoming(
#         init_image=init_image,
#         text_prompts=text_prompts,
#         ipadapter_strength=0.5,
#         control_strength=0.5,
#         height=1280,
#         width=1280,
#         seed=seed,
#         steps=8,
#     )


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

    # with gutils.log_time(f"Generating synthetic data for {task}", logger):
    #     func = getattr(sys.modules[__name__], generative_function_name)
    #     kwargs = task_config.synthetic_generation_config.kwargs

    func = getattr(sys.modules[__name__], generative_function_name)
    kwargs = task_config.synthetic_generation_config.kwargs

    return await func(**kwargs)
