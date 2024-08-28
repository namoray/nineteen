from functools import partial
from fastapi import Depends, HTTPException

from fiber.miner.security.encryption import decrypt_general_payload
from pydantic import BaseModel
from core.models import payload_models
from fastapi.routing import APIRouter
from fiber.logging_utils import get_logger
from miner import constants as mcst

from miner.logic.image import get_image_from_server
from fiber.miner.core.configuration import Config
from fiber.miner.dependencies import get_config

logger = get_logger(__name__)


async def _process_image_request(
    decrypted_payload: BaseModel,
    config: Config,
    post_endpoint: str,
) -> payload_models.ImageResponse:
    image_response = await get_image_from_server(
        httpx_client=config.httpx_client,
        body=decrypted_payload,
        post_endpoint=post_endpoint,
        timeout=30,
    )
    if image_response is None or (image_response.get("image_b64") is None and image_response.get("is_nsfw") is None):
        logger.debug(f"Image response: {image_response}")
        raise HTTPException(status_code=500, detail="Image generation failed")
    return payload_models.ImageResponse(**image_response)


async def text_to_image(
    decrypted_payload: payload_models.TextToImagePayload = Depends(
        partial(decrypt_general_payload, payload_models.TextToImagePayload)
    ),
    config: Config = Depends(get_config),
) -> payload_models.ImageResponse:
    return await _process_image_request(decrypted_payload, config, mcst.TEXT_TO_IMAGE_SERVER_ENDPOINT)


async def image_to_image(
    decrypted_payload: payload_models.ImageToImagePayload = Depends(
        partial(decrypt_general_payload, payload_models.ImageToImagePayload)
    ),
    config: Config = Depends(get_config),
) -> payload_models.ImageResponse:
    return await _process_image_request(decrypted_payload, config, mcst.IMAGE_TO_IMAGE_SERVER_ENDPOINT)


async def inpaint(
    decrypted_payload: payload_models.InpaintPayload = Depends(
        partial(decrypt_general_payload, payload_models.InpaintPayload)
    ),
    config: Config = Depends(get_config),
) -> payload_models.ImageResponse:
    return await _process_image_request(decrypted_payload, config, mcst.INPAINT_SERVER_ENDPOINT)


async def avatar(
    decrypted_payload: payload_models.AvatarPayload = Depends(
        partial(decrypt_general_payload, payload_models.AvatarPayload)
    ),
    config: Config = Depends(get_config),
) -> payload_models.ImageResponse:
    return await _process_image_request(decrypted_payload, config, mcst.AVATAR_SERVER_ENDPOINT)


def factory_router() -> APIRouter:
    router = APIRouter()
    router.add_api_route("/text-to-image", text_to_image, tags=["Subnet"], methods=["POST"])
    router.add_api_route("/image-to-image", image_to_image, tags=["Subnet"], methods=["POST"])
    router.add_api_route("/inpaint", inpaint, tags=["Subnet"], methods=["POST"])
    router.add_api_route("/avatar", avatar, tags=["Subnet"], methods=["POST"])
    return router
