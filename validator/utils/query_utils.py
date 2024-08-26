import base64
import binascii
import io
from validator.utils import (
    query_utils as qutils,
)
from PIL import Image
import random
import numpy as np
from core.logging import get_logger

logger = get_logger(__name__)


def pil_to_base64(image: Image, format: str = "JPEG") -> str:
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


def base64_to_pil(image_b64: str) -> Image.Image:
    try:
        image_data = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(image_data))
        return image
    except binascii.Error:
        return None


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
            numpy_image[rand_y, rand_x, i] = np.clip(int(numpy_image[rand_y, rand_x, i]) + change, 0, 255)

    pil_image = Image.fromarray(numpy_image)

    if pil_image.mode == "RGBA":
        pil_image = pil_image.convert("RGB")

    new_image = qutils.pil_to_base64(pil_image)
    return new_image
