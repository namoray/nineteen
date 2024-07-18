import random

from models import base_models, utility_models
from validator.utils import (
    synthetic_utils as sutils,
    synthetic_constants as scst,
)
from core import dataclasses as dc

import markovify
import datasets
import diskcache
from functools import lru_cache

# NOTE: any danger here of massively gorwing cache?
@lru_cache(maxsize=1)
def markov_model_factory() -> markovify.Text:
    dataset = datasets.load_dataset("multi-train/coco_captions_1107")
    text = [i["query"] for i in dataset["train"]]
    markov_text_generation_model = markovify.Text(" ".join(text))
    return markov_text_generation_model
    
@lru_cache(maxsize=1)
def image_cache_factory() -> diskcache.Cache:
    cache = diskcache.Cache("./image_cache")
    return cache

def _get_markov_sentence(max_words: int = 10) -> str:
    markov_text_generation_model = markov_model_factory()
    text = None
    while text is None:
        text = markov_text_generation_model.make_sentence(max_words=max_words)
    return text


async def generate_chat_synthetic(model: str) -> base_models.ChatIncoming:
    user_content = _get_markov_sentence(max_words=80)
    messages = [utility_models.Message(content=user_content, role=utility_models.Role.user.value)]

    if random.random() < 0.1:
        messages.append(
            utility_models.Message(
                content=_get_markov_sentence(max_words=80),
                role=utility_models.Role.assistant.value,
            )
        )
        messages.append(
            utility_models.Message(
                content=_get_markov_sentence(max_words=80),
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
    positive_text = _get_markov_sentence(max_words=20)
    text_prompts = [utility_models.TextPrompt(text=positive_text, weight=1.0)]
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

    positive_text = _get_markov_sentence(max_words=20)
    text_prompts = [utility_models.TextPrompt(text=positive_text, weight=1.0)]
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
    positive_text = _get_markov_sentence(max_words=20)
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
    positive_text = _get_markov_sentence(max_words=20)
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
