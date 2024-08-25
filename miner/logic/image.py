import json
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
        error_details = {
            "status_code": error.response.status_code,
            "request_url": str(error.request.url),
            "request_method": error.request.method,
            "request_headers": dict(error.request.headers),
            "request_body": json.loads(error.request.content.decode()) if error.request.content else None,
            "response_headers": dict(error.response.headers),
            "response_body": error.response.text,
        }
        logger.error(f"Detailed error information:\n{json.dumps(error_details, indent=2)}")
        logger.error(f"Status error when getting an image; response {error.response.status_code} while making request to {endpoint}")
        return None
    except httpx.RequestError as error:
        logger.warning(f"Request error getting an image; An error occurred while making request to {endpoint}: {error}")
        return None
