from functools import partial
from fastapi import Depends

from fiber.miner.security.encryption import decrypt_general_payload
from core.models import base_models
from fastapi.routing import APIRouter


async def text_to_speech(
    decrypted_payload: base_models.TextToSpeechRequest = Depends(
        partial(decrypt_general_payload, base_models.TextToSpeechRequest)
    ),
):
    return {"status": "Text-to-speech request received"}


async def capacity(
    decrypted_payload: base_models.TextToSpeechRequest = Depends(
        partial(decrypt_general_payload, base_models.TextToSpeechRequest)
    ),
) -> base_models.CapacityResponse:
    return {}


def factory_router() -> APIRouter:
    router = APIRouter()
    router.add_api_route("/text-to-speech", text_to_speech, tags=["Subnet"], methods=["POST"])
    router.add_api_route("/capacity", capacity, tags=["Subnet"], methods=["GET"])
    return router
