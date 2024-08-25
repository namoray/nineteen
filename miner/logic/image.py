import httpx
from pydantic import BaseModel
from core.logging import get_logger

logger = get_logger(__name__)

# TODO: fix
IMAGE_WORKER_ADDRESS = "http://62.169.159.78:6918/"


async def get_image_from_server(
    httpx_client: httpx.AsyncClient, body: BaseModel, post_endpoint: str, timeout: float = 20.0
) -> dict | None:
    endpoint = IMAGE_WORKER_ADDRESS.rstrip("/") + "/" + post_endpoint

    try:
        response = await httpx_client.post(endpoint, json=body.model_dump(), timeout=timeout)
        response.raise_for_status()

        data = response.json()
        return data

    except httpx.HTTPStatusError as error:
        logger.warning(
            f"Status error when getting an image; response {error.response.status_code} while making request to {endpoint}: {error}"
        )
        return None
    except httpx.RequestError as error:
        logger.warning(f"Request error getting an image; An error occurred while making request to {endpoint}: {error}")
        return None
