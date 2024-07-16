from typing import AsyncGenerator
from core import utils as cutils
from models import base_models

from PIL import Image
import random
import numpy as np


def alter_image(
    pil_image: Image.Image,
) -> str:
    numpy_image = np.array(pil_image)
    for _ in range(3):
        rand_x, rand_y = (
            random.randint(0, pil_image.width - 1),
            random.randint(0, pil_image.height - 1),
        )

        for i in range(3):
            change = random.choice([-1, 1])
            numpy_image[rand_y, rand_x, i] = np.clip(numpy_image[rand_y, rand_x, i] + change, 0, 255)

    pil_image = Image.fromarray(numpy_image)

    if pil_image.mode == "RGBA":
        pil_image = pil_image.convert("RGB")

    new_image = cutils.pil_to_base64(pil_image)
    return new_image


def alter_clip_body(
    body: base_models.ClipEmbeddingsIncoming,
) -> base_models.ClipEmbeddingsIncoming:
    if body.image_b64s is None:
        return body

    new_images = []
    for image in body.image_b64s:
        pil_image = cutils.base64_to_pil(image)
        new_image = alter_image(pil_image)
        new_images.append(new_image)

    body.image_b64s = new_images
    return body


async def consume_generator(generator: AsyncGenerator) -> None:
    async for _ in generator:
        pass
