from models import utility_models
from pydantic import BaseModel
from config.miner_config import config as config
import httpx
from core import bittensor_overrides as bt



async def get_image_from_server(body: BaseModel, post_endpoint: str, timeout: float = 20.0):
    endpoint = config.image_worker_url + post_endpoint
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(endpoint, json=body.dict())
            response.raise_for_status()

            data = response.json()
            image_response = utility_models.ImageResponseBody(**data)
            return image_response

        except httpx.HTTPStatusError as error:
            bt.logging.warning(
                f"Status error when getting an image; response {error.response.status_code} while making request to {endpoint}: {error}"
            )
        # Sometimes error is logging as none, need some more info here!
        except httpx.RequestError as error:
            bt.logging.warning(
                f"Request error getting an image; An error occurred while making request to {endpoint}: {error}"
            )
