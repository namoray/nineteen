from functools import partial
from fastapi import Depends

from fiber.miner.security.encryption import decrypt_general_payload
from core.models import base_models
from fastapi.routing import APIRouter
from core.tasks_config import TASK_TO_CONFIG


async def text_to_speech(
    decrypted_payload: base_models.TextToSpeechRequest = Depends(
        partial(decrypt_general_payload, base_models.TextToSpeechRequest)
    ),
):
    return {"status": "Text-to-speech request received"}


async def capacity() -> dict[str, float]:
    return {task: config.max_capacity for task, config in TASK_TO_CONFIG.items()}


def factory_router() -> APIRouter:
    router = APIRouter()
    router.add_api_route("/text-to-speech", text_to_speech, tags=["Subnet"], methods=["POST"])
    router.add_api_route("/capacity", capacity, tags=["Subnet"], methods=["GET"])
    return router
