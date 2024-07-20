from core import bittensor_overrides as bt
from models import base_models
from operation_logic import utils as operation_utils

POST_ENDPOINT = "avatar"


async def avatar_logic(
    body: base_models.AvatarIncoming,
) -> base_models.AvatarOutgoing:
    output = base_models.AvatarOutgoing(image_b64=None)

    image_response_body = await operation_utils.get_image_from_server(body, POST_ENDPOINT, timeout=40)

    # If safe for work but still no images, something went wrong probably
    if image_response_body is None or image_response_body.image_b64 is None and not image_response_body.is_nsfw:
        output.error_message = "Some error from the generation :/"
        return output

    if image_response_body.is_nsfw:
        bt.logging.info("NSFW image detected 👿, returning a corresponding error and no image")
        output.image_b64 = None
        output.is_nsfw = True
    else:
        bt.logging.info("✅ Used a face, got an image ✨")
        output.image_b64 = image_response_body.image_b64
        output.is_nsfw = False

    output.clip_embeddings = image_response_body.clip_embeddings
    output.image_hashes = image_response_body.image_hashes
    return output
