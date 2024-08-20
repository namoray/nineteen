import base64
from functools import partial
import json
import random
from fastapi import Depends

from fastapi.responses import StreamingResponse
from fiber.miner.security.encryption import decrypt_general_payload
from core.models import request_models
from fastapi.routing import APIRouter
from core.tasks_config import TASK_TO_CONFIG


async def chat_completions(
    decrypted_payload: request_models.ChatRequest = Depends(
        partial(decrypt_general_payload, request_models.ChatRequest)
    ),
) -> StreamingResponse:
    async def iterator():
        for i in range(100):
            data = json.dumps({"choices": [{"delta": {"content": i, "role": "assistant"}}]})
            yield f"data: {data}\n\n"

    return StreamingResponse(iterator())


async def text_to_image(
    decrypted_payload: request_models.ChatRequest = Depends(
        partial(decrypt_general_payload, request_models.ChatRequest)
    ),
) -> request_models.TextToImageResponse:
    # Generate a 1024x1024 image with random pixels
    image_data = bytearray()
    for _ in range(1024 * 1024 * 3):  # 3 bytes per pixel (RGB)
        image_data.append(random.randint(0, 255))

    # Encode the image data as a base64 string
    image_b64 = base64.b64encode(image_data).decode('utf-8')
    return request_models.TextToImageResponse(image_b64=image_b64)


async def capacity() -> dict[str, float]:
    return {task: config.max_capacity for task, config in TASK_TO_CONFIG.items()}


def factory_router() -> APIRouter:
    router = APIRouter()
    router.add_api_route("/chat/completions", chat_completions, tags=["Subnet"], methods=["POST"])
    router.add_api_route("/capacity", capacity, tags=["Subnet"], methods=["GET"])
    return router
