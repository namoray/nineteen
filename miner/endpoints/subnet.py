from functools import partial
from fastapi import Depends

from fastapi.responses import StreamingResponse
from fiber.miner.security.encryption import decrypt_general_payload
from core.models import payload_models
from fastapi.routing import APIRouter
from core.tasks_config import TASK_TO_CONFIG
from fiber.logging_utils import get_logger

from miner.logic.chat import chat_stream
from miner.logic.image import get_image_from_server
from fiber.miner.core.configuration import Config
from fiber.miner.dependencies import get_config

logger = get_logger(__name__)


async def chat_completions(
    decrypted_payload: payload_models.ChatPayload = Depends(
        partial(decrypt_general_payload, payload_models.ChatPayload)
    ),
    config: Config = Depends(get_config),
) -> StreamingResponse:
    decrypted_payload.model = "NousResearch/Hermes-3-Llama-3.1-8B"
    generator = chat_stream(config.httpx_client, decrypted_payload)

    return StreamingResponse(generator, media_type="text/event-stream")


async def text_to_image(
    decrypted_payload: payload_models.TextToImageRequest = Depends(
        partial(decrypt_general_payload, payload_models.TextToImageRequest)
    ),
    config: Config = Depends(get_config),
) -> payload_models.TextToImageResponse:
    image_response = await get_image_from_server(
        httpx_client=config.httpx_client, body=decrypted_payload, post_endpoint="text-to-image", timeout=15
    )
    return payload_models.TextToImageResponse(**image_response)


async def capacity() -> dict[str, float]:
    return {task: config.max_capacity for task, config in TASK_TO_CONFIG.items()}


def factory_router() -> APIRouter:
    router = APIRouter()
    router.add_api_route("/capacity", capacity, tags=["Subnet"], methods=["GET"])
    router.add_api_route("/chat/completions", chat_completions, tags=["Subnet"], methods=["POST"])
    router.add_api_route("/text-to-image", text_to_image, tags=["Subnet"], methods=["POST"])
    return router


# docker run --runtime nvidia --gpus all \ -v ~/.cache/huggingface:/root/.cache/huggingface \ -p 8000:8000 \ --ipc=host \ vllm/vllm-openai:latest \ --model unsloth/Meta-Llama-3.1-8B-Instruct --tokenizer tau-vision/llama-tokenizer-fix
 