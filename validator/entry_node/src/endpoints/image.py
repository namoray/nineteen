import json
from typing import Any
import uuid
from fastapi import Depends, HTTPException
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from core.logging import get_logger
from fastapi.routing import APIRouter
from core.models import payload_models
from core.tasks import Task
from core.tasks_config import get_task_config
from validator.entry_node.src.core.configuration import Config
from validator.entry_node.src.core.dependencies import get_config
from validator.utils import redis_constants as rcst, generic_constants as gcst
from validator.entry_node.src.models import request_models
import asyncio

from redis.asyncio.client import PubSub

from validator.utils.generic_dataclasses import GenericResponse

logger = get_logger(__name__)


def _construct_organic_message(payload: dict, job_id: str, task: str) -> dict[str, Any]:
    return json.dumps({"query_type": gcst.ORGANIC, "query_payload": payload, "task": task, "job_id": job_id})


async def _wait_for_acknowledgement(pubsub: PubSub, job_id: str) -> bool:
    async for message in pubsub.listen():
        channel = message["channel"].decode()
        if channel == f"{gcst.ACKNLOWEDGED}:{job_id}":
            logger.info(f"Job {job_id} confirmed by worker")
            break
    await pubsub.unsubscribe(f"{gcst.ACKNLOWEDGED}:{job_id}")
    return True


async def _collect_single_result(pubsub: PubSub, job_id: str) -> dict:
    async for message in pubsub.listen():
        # logger.debug(f"GOT MESSAGE: {message}")
        try:
            if message["type"] == "message" and gcst.ACKNLOWEDGED:
                result = json.loads(message["data"].decode())
                if gcst.ACKNLOWEDGED in result:
                    continue
                status_code = result[gcst.STATUS_CODE]
                if status_code >= 400:
                    raise HTTPException(status_code=status_code, detail=result[gcst.ERROR_MESSAGE])
                break
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON for message: {message}. Error: {e}")
            continue
    await pubsub.unsubscribe(f"{rcst.JOB_RESULTS}:{job_id}")
    return GenericResponse(**result)


async def make_non_stream_organic_query(redis_db: Redis, payload: dict[str, Any], task: str, timeout: float) -> GenericResponse:
    job_id = uuid.uuid4().hex
    organic_message = _construct_organic_message(payload=payload, job_id=job_id, task=task)

    await redis_db.lpush(rcst.QUERY_QUEUE_KEY, organic_message)

    pubsub = redis_db.pubsub()
    await pubsub.subscribe(f"{gcst.ACKNLOWEDGED}:{job_id}")

    try:
        await asyncio.wait_for(_wait_for_acknowledgement(pubsub, job_id), timeout=1)

        await pubsub.subscribe(f"{rcst.JOB_RESULTS}:{job_id}")
        return await asyncio.wait_for(_collect_single_result(pubsub, job_id), timeout=timeout)

    except asyncio.TimeoutError:
        logger.error(f"No confirmation received for job {job_id} within timeout period. Task: {task}, model: {payload['model']}")
        raise HTTPException(status_code=500, detail="Unable to proccess request")


async def text_to_image(
    text_to_image_request: request_models.TextToImageRequest,
    config: Config = Depends(get_config),
) -> request_models.ImageResponse:
    payload = request_models.text_to_image_to_payload(text_to_image_request)
    task_config = get_task_config(Task(payload.model))
    if task_config is None:
        raise HTTPException(status_code=400, detail="Invalid model")

    result = await make_non_stream_organic_query(redis_db=config.redis_db, payload=payload.model_dump(), task=payload.model, timeout=task_config.timeout)
    image_response = payload_models.ImageResponse(**json.loads(result.content))
    if image_response.is_nsfw:
        raise HTTPException(status_code=403, detail="NSFW content detected")
    if image_response.image_b64 is None:
        raise HTTPException(status_code=500, detail="Unable to proccess request")
    return request_models.ImageResponse(image_b64=image_response.image_b64)


async def image_to_image(
    image_to_image_request: request_models.ImageToImageRequest,
    config: Config = Depends(get_config),
) -> request_models.ImageResponse:
    
    payload = await request_models.image_to_image_to_payload(image_to_image_request, httpx_client=config.httpx_client, prod=config.prod)
    task_config = get_task_config(Task(payload.model))
    if task_config is None:
        raise HTTPException(status_code=400, detail="Invalid model")

    result = await make_non_stream_organic_query(redis_db=config.redis_db, payload=payload.model_dump(), task=payload.model, timeout=task_config.timeout)
    image_response = payload_models.ImageResponse(**json.loads(result.content))
    if image_response.is_nsfw:
        raise HTTPException(status_code=403, detail="NSFW content detected")
    if image_response.image_b64 is None:
        raise HTTPException(status_code=500, detail="Unable to proccess request")
    return request_models.ImageResponse(image_b64=image_response.image_b64)


router = APIRouter()
router.add_api_route("/v1/text-to-image", text_to_image, methods=["POST"], tags=["Text"])
router.add_api_route("/v1/image-to-image", image_to_image, methods=["POST"], tags=["Image"])

