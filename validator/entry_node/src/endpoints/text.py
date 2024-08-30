import json
from typing import Any, AsyncGenerator
import uuid
from fastapi import Depends, HTTPException
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from core.logging import get_logger
from fastapi.routing import APIRouter
from validator.entry_node.src.core.configuration import Config
from validator.entry_node.src.core.dependencies import get_config
from validator.utils import redis_constants as rcst, generic_constants as gcst
from validator.entry_node.src.models import request_models
import asyncio

from redis.asyncio.client import PubSub

logger = get_logger(__name__)


def _construct_organic_message(payload: dict, job_id: str, task: str) -> dict[str, Any]:
    return json.dumps({"query_type": gcst.ORGANIC, "query_payload": payload, "task": task, "job_id": job_id})


async def _wait_for_acknowledgement(pubsub: PubSub, job_id: str) -> bool:
    async for message in pubsub.listen():
        channel = message["channel"].decode()
        if channel == f"{gcst.ACKNLOWEDGED}:{job_id}" and message["type"] == "message":
            logger.info(f"Job {job_id} confirmed by worker")
            break
    await pubsub.unsubscribe(f"{gcst.ACKNLOWEDGED}:{job_id}")
    return True


async def _stream_results(pubsub: PubSub, job_id: str, first_chunk: str) -> AsyncGenerator[str, None]:
    yield first_chunk
    async for message in pubsub.listen():
        logger.debug(f"GOT MESSAGE: {message}")
        channel = message["channel"].decode()

        if channel == f"{rcst.JOB_RESULTS}:{job_id}" and message["type"] == "message":
            result = json.loads(message["data"].decode())
            if gcst.ACKNLOWEDGED in result:
                continue
            status_code = result[gcst.STATUS_CODE]
            if status_code >= 400:
                raise HTTPException(status_code=status_code, detail=result[gcst.ERROR_MESSAGE])

            content = result[gcst.CONTENT]
            yield content
            if "[DONE]" in content:
                break
    await pubsub.unsubscribe(f"{rcst.JOB_RESULTS}:{job_id}")


async def make_stream_organic_query(
    redis_db: Redis,
    payload: dict[str, Any],
    task: str,
) -> AsyncGenerator[str, None]:
    job_id = uuid.uuid4().hex
    organic_message = _construct_organic_message(payload=payload, job_id=job_id, task=task)

    await redis_db.lpush(rcst.QUERY_QUEUE_KEY, organic_message)

    pubsub = redis_db.pubsub()
    await pubsub.subscribe(f"{gcst.ACKNLOWEDGED}:{job_id}")

    try:
        await asyncio.wait_for(_wait_for_acknowledgement(pubsub, job_id), timeout=1)

        await pubsub.subscribe(f"{rcst.JOB_RESULTS}:{job_id}")

        async for message in pubsub.listen():
            if message["type"] == "message" and message["channel"].decode() == f"{rcst.JOB_RESULTS}:{job_id}":
                result = json.loads(message["data"].decode())
                if gcst.STATUS_CODE in result and result[gcst.STATUS_CODE] >= 400:
                    raise HTTPException(status_code=result[gcst.STATUS_CODE], detail=result[gcst.ERROR_MESSAGE])
                first_chunk = result[gcst.CONTENT]
                break
        return _stream_results(pubsub, job_id, first_chunk)

    except asyncio.TimeoutError:
        logger.error(f"Query node down? No confirmation received for job {job_id} within timeout period. Task: {task}, model: {payload['model']}")
        raise HTTPException(status_code=500, detail="Unable to process request")


async def chat(
    chat_request: request_models.ChatRequest,
    config: Config = Depends(get_config),
) -> StreamingResponse:
    payload = request_models.chat_to_payload(chat_request)

    try:
        text_generator = await make_stream_organic_query(
            redis_db=config.redis_db, payload=payload.model_dump(), task=payload.model
        )
        return StreamingResponse(text_generator, media_type="sse")
    except HTTPException as http_exc:
        logger.info(f"HTTPException in chat endpoint: {str(http_exc)}")
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


router = APIRouter()
router.add_api_route("/v1/chat/completions", chat, methods=["POST"], tags=["Text"])
