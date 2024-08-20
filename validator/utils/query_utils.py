# import base64
# import binascii
# import io
# from typing import AsyncGenerator
# from validator.utils import (
#     query_constants as qcst,
#     query_utils as qutils,
#     redis_constants as rcst,
# )
# from core import tasks_config as tcfg
# from PIL import Image
# import random
# import numpy as np
# import time
# from typing import Tuple
# from core.logging import get_logger
# from redis.asyncio import Redis

# logger = get_logger(__name__)


# def pil_to_base64(image: Image, format: str = "JPEG") -> str:
#     buffered = io.BytesIO()
#     image.save(buffered, format=format)
#     img_str = base64.b64encode(buffered.getvalue()).decode()
#     return img_str


# def base64_to_pil(image_b64: str) -> Image.Image:
#     try:
#         image_data = base64.b64decode(image_b64)
#         image = Image.open(io.BytesIO(image_data))
#         return image
#     except binascii.Error:
#         return None


# def alter_image(
#     pil_image: Image.Image,
# ) -> str:
#     numpy_image = np.array(pil_image)
#     for _ in range(3):
#         rand_x, rand_y = (
#             random.randint(0, pil_image.width - 1),
#             random.randint(0, pil_image.height - 1),
#         )

#         for i in range(3):
#             change = random.choice([-1, 1])
#             numpy_image[rand_y, rand_x, i] = np.clip(int(numpy_image[rand_y, rand_x, i]) + change, 0, 255)

#     pil_image = Image.fromarray(numpy_image)

#     if pil_image.mode == "RGBA":
#         pil_image = pil_image.convert("RGB")

#     new_image = qutils.pil_to_base64(pil_image)
#     return new_image


# def alter_clip_body(
#     body: base_models.ClipEmbeddingsIncoming,
# ) -> base_models.ClipEmbeddingsIncoming:
#     if body.image_b64s is None:
#         return body

#     new_images = []
#     for image in body.image_b64s:
#         pil_image = qutils.base64_to_pil(image)
#         new_image = alter_image(pil_image)
#         new_images.append(new_image)

#     body.image_b64s = new_images
#     return body

