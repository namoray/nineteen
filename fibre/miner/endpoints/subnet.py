from functools import partial
from fastapi import Depends

from fibre.miner.security.encryption import decrypt_general_payload
from core.models import base_models
from fastapi.routing import APIRouter


async def text_to_speech(
    decrypted_payload: base_models.TextToSpeechRequest = Depends(
        partial(decrypt_general_payload, base_models.TextToSpeechRequest)
    ),
):
    print(decrypted_payload)
    return {"status": "Text-to-speech request received"}


def factory_router() -> APIRouter:
    router = APIRouter()
    router.add_api_route("/text-to-speech", text_to_speech, tags=["Subnet"], methods=["POST"])
    return router
