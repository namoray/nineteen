import base64
from functools import partial
import random
from fastapi import Depends

from fastapi.responses import StreamingResponse
from fiber.miner.security.encryption import decrypt_general_payload
from core.models import payload_models
from fastapi.routing import APIRouter
from core.models.utility_models import ImageHashes
from core.tasks_config import TASK_TO_CONFIG
from fiber.logging_utils import get_logger

from miner.logic.chat import chat_stream


logger = get_logger(__name__)


async def chat_completions(
    decrypted_payload: payload_models.ChatPayload = Depends(
        partial(decrypt_general_payload, payload_models.ChatPayload)
    ),
) -> StreamingResponse:
    decrypted_payload.model = "NousResearch/Hermes-3-Llama-3.1-8B"
    generator = chat_stream(decrypted_payload)

    return StreamingResponse(generator, media_type="text/event-stream")


async def text_to_image(
    decrypted_payload: payload_models.TextToImageRequest = Depends(
        partial(decrypt_general_payload, payload_models.TextToImageRequest)
    ),
) -> payload_models.TextToImageResponse:
    image_data = bytearray()
    for _ in range(1024 * 1024 * 3):  # 3 bytes per pixel (RGB)
        image_data.append(random.randint(0, 255))

    # Encode the image data as a base64 string
    image_b64 = base64.b64encode(image_data).decode("utf-8")
    response = payload_models.TextToImageResponse(
        image_b64=image_b64,
        is_nsfw=False,
        clip_embeddings=[],
        image_hashes=ImageHashes(average_hash="", perceptual_hash="", difference_hash="", color_hash=""),
    )
    return response


async def capacity() -> dict[str, float]:
    return {task: config.max_capacity for task, config in TASK_TO_CONFIG.items()}


def factory_router() -> APIRouter:
    router = APIRouter()
    router.add_api_route("/capacity", capacity, tags=["Subnet"], methods=["GET"])
    router.add_api_route("/chat/completions", chat_completions, tags=["Subnet"], methods=["POST"])
    router.add_api_route("/text-to-image", text_to_image, tags=["Subnet"], methods=["POST"])
    return router


# docker run --runtime nvidia --gpus all \ -v ~/.cache/huggingface:/root/.cache/huggingface \ -p 8000:8000 \ --ipc=host \ vllm/vllm-openai:latest \ --model unsloth/Meta-Llama-3.1-8B-Instruct --tokenizer tau-vision/llama-tokenizer-fix
