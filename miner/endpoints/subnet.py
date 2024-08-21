import base64
from functools import partial
import json
import random
from fastapi import Depends

from fastapi.responses import StreamingResponse
from fiber.miner.security.encryption import decrypt_general_payload
import httpx
from core.models import request_models
from fastapi.routing import APIRouter
from core.models.utility_models import ImageHashes
from core.tasks_config import TASK_TO_CONFIG
from fiber.logging_utils import get_logger


logger = get_logger(__name__)


LLAMA_3_8B_ADDRESS = "http://62.169.159.78:8000/v1/chat/completions"


async def chat_completions(
    decrypted_payload: request_models.ChatRequest = Depends(
        partial(decrypt_general_payload, request_models.ChatRequest)
    ),
) -> StreamingResponse:
    
    decrypted_payload.model = "NousResearch/Hermes-3-Llama-3.1-8B"
    
    async def iterator():
        async with httpx.AsyncClient(timeout=90) as client:  # noqa
            async with client.stream("POST", LLAMA_3_8B_ADDRESS, json=decrypted_payload.model_dump()) as resp:
                async for chunk in resp.aiter_lines():
                    try:
                        received_event_chunks = chunk.split("\n\n")
                        for event in received_event_chunks:
                            if event == "":
                                continue
                            prefix, _, data = event.partition(":")
                            if data.strip() == "[DONE]":
                                break
                            loaded_chunk = json.loads(data)
                            content = loaded_chunk["choices"][0]["delta"].get("content", "")
                            logprobs_obj = loaded_chunk["choices"][0].get("logprobs", {})
                            if logprobs_obj:
                                logprob = logprobs_obj.get("content", [{}])[0].get("logprob")
                                data = json.dumps({"text": content, "logprob": logprob})
                                yield f"data: {data}\n\n"
                    except Exception as e:
                        logger.error(f"Error in streaming text from the server: {e}. Original chunk: {chunk}")
                        # Optionally, you can choose to yield an error message or continue silently
                        # yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(iterator(), media_type="text/event-stream")
    return StreamingResponse(iterator(), media_type="text/event-stream")


async def text_to_image(
    decrypted_payload: request_models.TextToImageRequest = Depends(
        partial(decrypt_general_payload, request_models.TextToImageRequest)
    ),
) -> request_models.TextToImageResponse:
    image_data = bytearray()
    for _ in range(1024 * 1024 * 3):  # 3 bytes per pixel (RGB)
        image_data.append(random.randint(0, 255))

    # Encode the image data as a base64 string
    image_b64 = base64.b64encode(image_data).decode("utf-8")
    response = request_models.TextToImageResponse(
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