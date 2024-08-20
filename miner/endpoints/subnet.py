from functools import partial
import json
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
):
    async def iterator():
        for i in range(100):
            data = json.dumps({"choices": [{"delta": {"content": i, "role": "assistant"}}]})
            yield f"data: {data}\n\n"
    
    return StreamingResponse(iterator())

async def text_to_image(
            decrypted_payload: request_models.ChatRequest = Depends(
        partial(decrypt_general_payload, request_models.ChatRequest)
    ),
    
):
    

async def capacity() -> dict[str, float]:
    return {task: config.max_capacity for task, config in TASK_TO_CONFIG.items()}


def factory_router() -> APIRouter:
    router = APIRouter()
    router.add_api_route("/chat/completions", chat_completions, tags=["Subnet"], methods=["POST"])
    router.add_api_route("/capacity", capacity, tags=["Subnet"], methods=["GET"])
    return router
