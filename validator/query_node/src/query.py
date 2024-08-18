import json
import time
from typing import Any, AsyncGenerator

import httpx
from core.models import utility_models
from core.tasks import Task
from validator.query_node.src.query_config import Config
from validator.query_node.src import utils

from validator.models import Contender
from fiber.validator import client
from fiber.chain_interactions.models import Node
from core import tasks_config as tcfg
from validator.utils import redis_constants as rcst

from fiber.logging_utils import get_logger


logger = get_logger(__name__)


def _load_sse_jsons(chunk: str) -> list[dict[str, Any]] | dict[str, str]:
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


async def _handle_event(config: Config, event: str, synthetic_query: bool, job_id: str) -> None:
    if synthetic_query:
        return
    await config.redis_db.rpush(rcst.QUERY_RESULTS_KEY + ":" + job_id, event)


async def async_chain(first_chunk, async_gen):
    yield first_chunk  # manually yield the first chunk
    async for item in async_gen:
        yield item  # then yield from the original generator


async def consume_generator(
    config: Config,
    generator: AsyncGenerator,
    job_id: str,
    synthetic_query: bool,
    contender: Contender,
    node: Node,
    payload: dict,
    debug: bool = False,
) -> None:
    assert job_id
    task = contender.task

    logger.debug(
        f"Querying axon {node.node_id} for a stream, and task: {task}. Debug: {bool(debug)}. Synthetic: {synthetic_query}."
    )

    try:
        first_chunk = await generator.__anext__()
    except (StopAsyncIteration, httpx.ConnectError, httpx.ReadError, httpx.HTTPError) as e:
        logger.error(f"Error when querying node: {node.node_id} for task: {task}. Error: {e}")
        query_result = utility_models.QueryResult(
            node_id=node.node_id,
            task=task,
            success=False,
            node_hotkey=node.hotkey,
            formatted_response=None,
            status_code=500,
            response_time=None,
            error_message=None,
        )
        await utils.adjust_contender_from_result(config, query_result, contender, synthetic_query, payload=payload)
        return

    start_time, text_jsons, status_code, error_message = time.time(), [], 500, None

    async for text in async_chain(first_chunk, generator):
        first_message = True
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
                _handle_event(
                    config, event=f"data: {dumped_payload}\n\n", synthetic_query=synthetic_query, job_id=job_id
                )

        if len(text_jsons) > 0:
            last_payload = _get_formatted_payload("", False, add_finish_reason=True)
            _handle_event(config, event=f"data: {last_payload}\n\n", synthetic_query=synthetic_query, job_id=job_id)
            _handle_event(config, event="data: [DONE]\n\n", synthetic_query=synthetic_query, job_id=job_id)
            logger.info(f"✅ Successfully queried node: {node.node_id} for task: {task}")

        response_time = time.time() - start_time
        logger.debug(f"Got query result!. Success: {not first_message}. Response time: {response_time}")
        query_result = utility_models.QueryResult(
            formatted_response=text_jsons if len(text_jsons) > 0 else None,
            node_id=node.node_id,
            response_time=response_time,
            task=task,
            success=not first_message,
            node_hotkey=node.hotkey,
            status_code=status_code,
            error_message=error_message,
        )
        logger.debug(f"Query result: {query_result}")
        await utils.adjust_contender_from_result(config, query_result, contender, synthetic_query, payload=payload)
        await config.redis_db.expire(rcst.QUERY_RESULTS_KEY + ":" + job_id, 10)


async def query_node_stream(config: Config, contender: Contender, node: Node, payload: dict):
    try:
        address = client.construct_server_address(
            node,
            replace_with_docker_localhost=config.replace_with_docker_localhost,
            replace_with_localhost=config.replace_with_localhost,
        )
        logger.info(
            f"making a query to node: {node.node_id} for task: {contender.task}."
            f" address: {address}, endpoint: {tcfg.TASK_TO_CONFIG[Task(contender.task)].endpoint}"
            f"Payload: {payload}"
        )
        return client.make_streamed_post(
            httpx_client=config.httpx_client,
            server_address=address,
            validator_ss58_address=config.ss58_address,
            fernet=node.fernet,
            symmetric_key_uuid=node.symmetric_key_uuid,
            payload=payload,
            endpoint=tcfg.TASK_TO_CONFIG[Task(contender.task)].endpoint,
            timeout=tcfg.TASK_TO_CONFIG[Task(contender.task)].timeout,
        )
    except Exception as e:
        logger.error(f"Error when querying node: {node.node_id} for task: {contender.task}. Error: {e}")
        return None
