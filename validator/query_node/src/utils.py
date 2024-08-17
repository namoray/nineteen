import asyncio
import random
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from pydantic import BaseModel, ValidationError
from core.tasks import Task
from validator.db.src.database import PSQLDB
from validator.models import Contender
from core import bittensor_overrides as bt
from collections import OrderedDict
import json
from validator.utils import query_utils as qutils, work_and_speed_functions
from core.logging import get_logger
from validator.db.src import functions as db_functions

logger = get_logger(__name__)




def get_formatted_response(
    resulting_synapse: base_models.BaseSynapse, initial_synapse: bt.Synapse
) -> Optional[BaseModel]:
    if resulting_synapse and resulting_synapse.dendrite.status_code == 200 and resulting_synapse != initial_synapse:
        formatted_response = _extract_response(resulting_synapse, initial_synapse)
        return formatted_response
    else:
        return None


def _load_sse_jsons(chunk: str) -> Union[List[Dict[str, Any]], Dict[str, str]]:
    try:
        jsons = []
        received_event_chunks = chunk.split("\n\n")
        for event in received_event_chunks:
            if event == "":
                continue
            prefix, _, data = event.partition(":")
            if data.strip() == "[DONE]":
                break
            loaded_chunk = json.loads(data)
            jsons.append(loaded_chunk)
        return jsons
    except json.JSONDecodeError:
        try:
            loaded_chunk = json.loads(chunk)
            if "message" in loaded_chunk:
                return {
                    "message": loaded_chunk["message"],
                    "status_code": "429" if "bro" in loaded_chunk["message"] else "500",
                }
        except json.JSONDecodeError:
            ...

    return []


def _get_formatted_payload(content: str, first_message: bool, add_finish_reason: bool = False) -> str:
    delta_payload = {"content": content}
    if first_message:
        delta_payload["role"] = "assistant"
    choices_payload = {"delta": delta_payload}
    if add_finish_reason:
        choices_payload["finish_reason"] = "stop"
    payload = {
        "choices": [choices_payload],
    }

    dumped_payload = json.dumps(payload)
    return dumped_payload


async def _get_debug_text_generator():
    yield "This is a debug text generator. I will yield random numbers with small delays"

    for _ in range(500):
        yield f"{random.random()}"
        await asyncio.sleep(random.random() * 0.01)


async def query_miner_stream(
    psql_db: PSQLDB,
    axon: AxonInfo,
    contender: Contender,
    synapse: bt.Synapse,
    dendrite: bt.dendrite,
    synthetic_query: bool,
    debug: bool = False,
) -> AsyncIterator[str]:
    axon_uid = axon.axon_uid
    task = contender.task

    logger.debug(
        f"Querying axon {axon_uid} for a stream, and task: {task}. Debug: {bool(debug)}. Synthetic: {synthetic_query}."
    )

    if debug:
        text_generator = _get_debug_text_generator()
        async for text in text_generator:
            yield text
    else:
        logger.debug("getting axon stream")
        text_generator = await qutils.query_individual_axon_stream(
            synapse=synapse, dendrite=dendrite, axon=axon, axon_uid=axon_uid, log_requests_and_responses=False
        )

        time1 = time.time()
        text_jsons = []
        status_code = 200
        error_message = None
        if text_generator is not None:
            first_message = True
            async for text in text_generator:
                if isinstance(text, str):
                    try:
                        loaded_jsons = _load_sse_jsons(text)
                        if isinstance(loaded_jsons, dict):
                            status_code = loaded_jsons.get("status_code")
                            error_message = loaded_jsons.get("message")
                            break

                    except (IndexError, json.JSONDecodeError) as e:
                        logger.warning(f"Error {e} when trying to load text: {text}")
                        break

                    text_jsons.extend(loaded_jsons)
                    for text_json in loaded_jsons:
                        content = text_json.get("text", "")
                        if content == "":
                            continue
                        dumped_payload = _get_formatted_payload(content, first_message)
                        first_message = False
                        yield f"data: {dumped_payload}\n\n"

            if len(text_jsons) > 0:
                last_payload = _get_formatted_payload("", False, add_finish_reason=True)
                yield f"data: {last_payload}\n\n"
                yield "data: [DONE]\n\n"
                logger.info(f"✅ Successfully queried axon: {axon_uid} for task: {task}")

            response_time = time.time() - time1
            logger.debug(f"Got query result!. Success: {not first_message}. Response time: {response_time}")
            query_result = utility_models.QueryResult(
                formatted_response=text_jsons if len(text_jsons) > 0 else None,
                axon_uid=axon_uid,
                response_time=response_time,
                task=task,
                success=not first_message,
                node_hotkey=axon.hotkey,
                status_code=status_code,
                error_message=error_message,
            )

        await adjust_contender_from_result(psql_db, query_result, synapse, contender, synthetic_query)


async def adjust_contender_from_result(
    psql_db: PSQLDB,
    query_result: utility_models.QueryResult,
    synapse: bt.Synapse,
    contender: Contender,
    synthetic_query: bool,
):
    contender.total_requests_made += 1

    if synthetic_query:
        contender.synthetic_requests_still_to_make -= 1

    if query_result.status_code == 200 and query_result.success:
        work = work_and_speed_functions.calculate_work(query_result.task, query_result, synapse=synapse.model_dump())
        contender.consumed_capacity += work

        await db_functions.potentially_store_result_in_sql_lite_db(
            psql_db, query_result, query_result.task, synapse, synthetic_query=synthetic_query
        )
        logger.debug(f"Adjusted contender: {contender.id} for task: {query_result.task}")

    elif query_result.status_code == 429:
        contender.requests_429 += 1
    else:
        contender.requests_500 += 1
    return query_result


async def query_miner_no_stream(
    contender: Contender,
    synapse: bt.Synapse,
    outgoing_model: BaseModel,
    task: Task,
    dendrite: bt.dendrite,
    synthetic_query: bool,
) -> utility_models.QueryResult:
    axon_uid = contender.node_hotkey
    axon = contender.axon
    resulting_synapse, response_time = await qutils.query_individual_axon(
        synapse=synapse, dendrite=dendrite, axon=axon, uid=axon_uid, log_requests_and_responses=False
    )

    # IDE doesn't recognise the above typehints, idk why? :-(
    resulting_synapse: base_models.BaseSynapse
    response_time: float

    formatted_response = get_formatted_response(resulting_synapse, outgoing_model)
    if formatted_response is not None:
        bt.logging.info(f"✅ Successfully queried axon: {axon_uid} for task: {task}")
        query_result = utility_models.QueryResult(
            formatted_response=formatted_response,
            axon_uid=axon_uid,
            response_time=response_time,
            task=task,
            success=True,
            node_hotkey=contender.node_hotkey,
            status_code=resulting_synapse.axon.status_code,
            error_message=resulting_synapse.error_message,
        )
        # create_scoring_adjustment_task(query_result, synapse, contender, synthetic_query)
        return query_result

    elif task == Task.avatar:
        query_result = utility_models.QueryResult(
            formatted_response=formatted_response,
            axon_uid=axon_uid,
            response_time=response_time,
            task=task,
            success=False,
            node_hotkey=contender.node_hotkey,
            status_code=resulting_synapse.axon.status_code,
            error_message=resulting_synapse.error_message,
        )
        # create_scoring_adjustment_task(query_result, synapse, contender, synthetic_query)

    else:
        query_result = utility_models.QueryResult(
            formatted_response=None,
            axon_uid=axon_uid,
            response_time=None,
            error_message=resulting_synapse.axon.status_message,
            task=task,
            status_code=resulting_synapse.axon.status_code,
            success=False,
            node_hotkey=contender.node_hotkey,
        )
        # create_scoring_adjustment_task(query_result, synapse, contender, synthetic_query)
        return query_result


def _extract_response(resulting_synapse: base_models.BaseSynapse, outgoing_model: BaseModel) -> Optional[BaseModel]:
    try:
        formatted_response = outgoing_model(**resulting_synapse.dict())

        # If we're expecting a result (i.e. not nsfw), then try to deserialize
        if (hasattr(formatted_response, "is_nsfw") and not formatted_response.is_nsfw) or not hasattr(
            formatted_response, "is_nsfw"
        ):
            deserialized_result = resulting_synapse.deserialize()
            if deserialized_result is None:
                formatted_response = None

        return formatted_response
    except ValidationError as e:
        bt.logging.debug(f"Failed to deserialize for some reason: {e}")
        return None


# async def query_individual_axon_stream(
#     dendrite: bt.dendrite,
#     axon: bt.axon,
#     axon_uid: int,
#     synapse: bt.Synapse,
#     deserialize: bool = False,
#     log_requests_and_responses: bool = True,
# ):
#     synapse_name = synapse.__class__.__name__
#     if synapse_name not in cst.OPERATION_TIMEOUTS:
#         bt.logging.warning(f"Operation {synapse_name} not in operation_to_timeout, this is probably a mistake / bug 🐞")
#     if log_requests_and_responses:
#         bt.logging.info(f"Querying axon {axon_uid} for {synapse_name}")
#     response = await dendrite.forward(
#         axons=axon,
#         synapse=synapse,
#         connect_timeout=0.3,
#         response_timeout=5,  # if X seconds without any data, its boinked
#         deserialize=deserialize,
#         log_requests_and_responses=log_requests_and_responses,
#         streaming=True,
#     )
#     return response
