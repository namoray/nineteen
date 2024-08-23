import json
from typing import Any, AsyncGenerator
import uuid
from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from redis.asyncio import Redis
from core.tasks import Task
from core.logging import get_logger
from fastapi.routing import APIRouter
from validator.entry_node.src.core.configuration import Config
from validator.entry_node.src.core.dependencies import get_config
from validator.utils import redis_constants as rcst
from validator.entry_node.src.models import request_models
import asyncio

from redis.asyncio.client import PubSub
logger = get_logger(__name__)

router = APIRouter()


def _construct_organic_message(job_id: str, task: Task) -> dict[str, Any]:
    return json.dumps({"query_type": "organic", "query_payload": {"task": task, "job_id": job_id}})


async def _wait_for_confirmation(pubsub: PubSub, job_id: str) -> bool:
    async for message in pubsub.listen():
        if message["type"] == "message":
            channel = message["channel"].decode()
            if channel == f"job_confirmation_{job_id}":
                logger.info(f"Job {job_id} confirmed by worker")
                return True



async def _stream_results(pubsub: PubSub, job_id: str) -> AsyncGenerator[str, None]:
    async for message in pubsub.listen():
        if message["type"] == "message":
            channel = message["channel"].decode()
            if channel == f"job_result_{job_id}":
                result = json.loads(message["data"])
                yield json.dumps(result)
                if result.get("status") == "DONE":
                    break


async def make_organic_query(
    redis_db: Redis,
    payload: dict[str, Any],
    stream: bool,
    task: str,
) -> AsyncGenerator[str, None]:
    job_id = str(uuid.uuid4())
    organic_message = _construct_organic_message(job_id=job_id, task=task)

    await redis_db.lpush(rcst.QUERY_QUEUE_KEY, organic_message)

    pubsub = redis_db.pubsub()
    logger.debug("here!")
    await pubsub.subscribe(f"job_confirmation_{job_id}", f"job_result_{job_id}")

    try:
        await asyncio.wait_for(_wait_for_confirmation(pubsub, job_id), timeout=1)

        if stream:
            return _stream_results(pubsub, job_id)
        else:
            logger.error("No stream implemented yet")
            return
            async for result in _stream_results(pubsub, job_id):
                result_dict = json.loads(result)
                if result_dict.get("status") == "DONE":
                    return JSONResponse(content=result_dict)
    except asyncio.TimeoutError:
        logger.error(f"No confirmation received for job {job_id} within timeout period. Task: {task}, model: {payload['model']}")
        raise HTTPException(status_code=500, detail="Unable to proccess request")
    finally:
        await pubsub.unsubscribe(f"job_confirmation_{job_id}", f"job_result_{job_id}")


@router.post("/chat")
async def chat(
    chat_request: request_models.ChatRequest,
    config: Config = Depends(get_config),
) -> StreamingResponse:
    payload = request_models.chat_to_payload(chat_request)

    text_generator = await make_organic_query(
        redis_db=config.redis_db, payload=payload.model_dump(), stream=True, task=payload.model
    )
    return StreamingResponse(text_generator, media_type="sse")
