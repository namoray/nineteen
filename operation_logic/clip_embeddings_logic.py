import bittensor as bt

import httpx
from models import base_models
from pydantic import BaseModel
from typing import List, Optional
from config.miner_config import config as config


class ClipEmbeddingsResponse(BaseModel):
    clip_embeddings: Optional[List[List[float]]] = None


async def _get_clip_embeddings_from_server(body: BaseModel) -> ClipEmbeddingsResponse:
    clip_endpoint = config.image_worker_url + "clip-embeddings"

    try:
        async with httpx.AsyncClient(timeout=5) as client:  # noqa
            response = await client.post(clip_endpoint, json=body.dict())
    except httpx.HTTPStatusError as error:
        bt.logging.warning(
            f"Error getting an image; response {error.response.status_code} while making request to {clip_endpoint}: {error}"
        )
        raise 
    except httpx.RequestError as error:
        bt.logging.warning(
            f"Error getting an image; An error occurred while making request to {clip_endpoint}: {error}"
        )
        raise

    if response.status_code != 200:
        bt.logging.error(f"Request failed with status {response.status_code}, error message: {response.text}")
        return ClipEmbeddingsResponse()

    try:
        embeddings_response = ClipEmbeddingsResponse(**response.json())
    except Exception as e:
        bt.logging.error(f"Error occurred while processing the server response: {e}. Original response: {response}")
        raise

    return embeddings_response


async def clip_embeddings_logic(
    body: base_models.ClipEmbeddingsIncoming,
) -> base_models.ClipEmbeddingsOutgoing:
    output = base_models.ClipEmbeddingsOutgoing()

    clip_embeddings_response = await _get_clip_embeddings_from_server(body)
    embeddings = clip_embeddings_response.clip_embeddings
    output.clip_embeddings = clip_embeddings_response.clip_embeddings

    if embeddings is not None and len(embeddings) > 0:
        bt.logging.info(f"✅ {len(embeddings)} image embedding(s) generated. bang.")

    return output
