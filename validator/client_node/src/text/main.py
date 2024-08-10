"""
Review all this
"""

import json
import random
from typing import Any, AsyncGenerator, Type
import uuid
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.asyncio import Redis
from models import base_models, synapses, utility_models, request_models
from starlette.responses import StreamingResponse
from generic import bittensor_overrides as bt
from fastapi.routing import APIRouter
from generic.tasks import Task
from validator.utils import redis_utils as rutils, redis_constants as rcst
from generic.logging import get_logger


logger = get_logger(__name__)

# TODO: no global var plz
redis_db = Redis(host="redis")
router = APIRouter()


def get_synapse_from_body(
    body: BaseModel,
    synapse_model: Type[bt.Synapse],
) -> bt.Synapse:
    body_dict = body.model_dump()
    body_dict["seed"] = random.randint(1, 10000)
    synapse = synapse_model(**body_dict)
    return synapse


def _construct_organic_message(job_id: str, task: Task) -> dict[str, Any]:
    return json.dumps({"query_type": "organic", "query_payload": {"task": task.value, "job_id": job_id}})


async def make_organic_query(
    redis_db: Redis,
    synapse: bt.Synapse,
    outgoing_model: Type[base_models.BaseOutgoing],
    stream: bool,
    task: Task,
) -> JSONResponse | AsyncGenerator:
    job_id = str(uuid.uuid4())
    organic_message = _construct_organic_message(job_id=job_id, task=task)
    await rutils.add_str_to_redis_list(redis_db, rcst.QUERY_QUEUE_KEY, organic_message)

    # REPLACE BELOW WITH A STREAM, NOT NEVER ENDING QUEUE READS
    done = False
    while not done:
        _, result = await redis_db.blpop(rcst.QUERY_RESULTS_KEY + ":" + job_id)
        logger.info(result)
        yield result
        if "DONE" in result.decode():
            break
    


@router.post("/chat")
async def chat(
    body: request_models.ChatRequest,
) -> StreamingResponse:
    synapse: synapses.Chat = get_synapse_from_body(
        body=body,
        synapse_model=synapses.Chat,
    )

    if synapse.model == utility_models.ChatModels.mixtral.value:
        task = Task.chat_mixtral
    elif synapse.model == utility_models.ChatModels.llama_3.value:
        task = Task.chat_llama_3
    else:
        raise HTTPException(status_code=400, detail="Invalid model provided")

    text_generator = make_organic_query(
        redis_db=redis_db, synapse=synapse, outgoing_model=base_models.ChatOutgoing, stream=True, task=task
    )
    if not isinstance(text_generator, AsyncGenerator):
        return text_generator

    return StreamingResponse(text_generator, media_type="text/plain")
