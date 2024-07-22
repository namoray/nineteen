"""
Review all this
"""

import random
from typing import AsyncGenerator, Type
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from models import base_models, synapses, utility_models, request_models
from starlette.responses import StreamingResponse
from core import bittensor_overrides as bt
from fastapi.routing import APIRouter
from core import Task

router = APIRouter()


def get_synapse_from_body(
    body: BaseModel,
    synapse_model: Type[bt.Synapse],
) -> bt.Synapse:
    body_dict = body.model_dump()
    body_dict["seed"] = random.randint(1, 10000)
    synapse = synapse_model(**body_dict)
    return synapse


async def make_organic_query(
    synapse: bt.Synapse,
    outgoing_model: Type[base_models.BaseOutgoing],
    stream: bool,
    task: Task,
) -> JSONResponse | AsyncGenerator: ...


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

    text_generator = await make_organic_query(
        synapse=synapse, outgoing_model=base_models.ChatOutgoing, stream=True, task=task
    )
    if not isinstance(text_generator, AsyncGenerator):
        return text_generator

    return StreamingResponse(text_generator, media_type="text/plain")
