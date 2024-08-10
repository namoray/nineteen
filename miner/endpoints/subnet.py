from functools import partial
from fastapi import Depends

from miner.encryption import decrypt_general_payload
from models import base_models
from fastapi.routing import APIRouter


async def text_to_speech_endpoint(
    decrypted_payload: base_models.TextToSpeechRequest = Depends(
        partial(decrypt_general_payload, base_models.TextToSpeechRequest)
    ),
):
    print(decrypted_payload)
    return {"status": "Text-to-speech request received"}


def factory_router() -> APIRouter:
    router = APIRouter()
    router.add_api_route("/text-to-speech", text_to_speech_endpoint, tags=["text-to-speech"])
    return router
