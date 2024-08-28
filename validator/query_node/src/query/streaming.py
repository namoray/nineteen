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
from validator.utils import generic_utils, redis_constants as rcst
from validator.utils import generic_constants as gcst
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


async def _handle_event(
    config: Config,
    content: str | None,
    synthetic_query: bool,
    job_id: str,
    status_code: int,
    error_message: str | None = None,
) -> None:
    # TODO: Uncomment
    if synthetic_query:
        return
    if content is not None:
        if isinstance(content, dict):
            content = json.dumps(content)
        await config.redis_db.publish(f"{rcst.JOB_RESULTS}:{job_id}", generic_utils.get_success_event(content=content, job_id=job_id, status_code=status_code))
    else:
        await config.redis_db.publish(f"{rcst.JOB_RESULTS}:{job_id}", generic_utils.get_error_event(job_id=job_id, error_message=error_message, status_code=status_code))


async def async_chain(first_chunk, async_gen):
    yield first_chunk  # manually yield the first chunk
    async for item in async_gen:
        yield item  # then yield from the original generator


def construct_500_query_result(node: Node, task: Task) -> utility_models.QueryResult:
    query_result = utility_models.QueryResult(
        node_id=node.node_id,
        task=task,
        success=False,
        node_hotkey=node.hotkey,
        formatted_response=None,
        status_code=500,
        response_time=None,
    )
    return query_result


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

    try:
        first_chunk = await generator.__anext__()
    except (StopAsyncIteration, httpx.ConnectError, httpx.ReadError, httpx.HTTPError, httpx.ReadTimeout, Exception) as e:
        error_type = type(e).__name__
        error_details = str(e)

        logger.error(f"Error when querying node: {node.node_id} for task: {task}. Error: {error_type} - {error_details}")
        query_result = construct_500_query_result(node, task)
        await utils.adjust_contender_from_result(config, query_result, contender, synthetic_query, payload=payload)
        return
  
    start_time, text_jsons, status_code, first_message = time.time(), [], 200, True
    try:
        async for text in async_chain(first_chunk, generator):
            if isinstance(text, bytes):
                text = text.decode()
            if isinstance(text, str):
                try:
                    loaded_jsons = _load_sse_jsons(text)
                    if isinstance(loaded_jsons, dict):
                        status_code = loaded_jsons.get(gcst.STATUS_CODE)
                        break

                except (IndexError, json.JSONDecodeError) as e:
                    logger.warning(f"Error {e} when trying to load text: {text}")
                    break
                
                text_jsons.extend(loaded_jsons)
                for text_json in loaded_jsons:
                    if not isinstance(text_json, dict):
                        first_message = True  # Janky, but so we mark it as a fail
                        break
                    try:
                        _ = text_json["choices"][0]["delta"]["content"]
                    except KeyError:
                        first_message = True  # Janky, but so we mark it as a fail
                        break

                    dumped_payload = json.dumps(text_json)
                    first_message = False
                    await _handle_event(
                        config, event=f"data: {dumped_payload}\n\n", synthetic_query=synthetic_query, job_id=job_id
                    )

        if len(text_jsons) > 0:
            last_payload = _get_formatted_payload("", False, add_finish_reason=True)
            await _handle_event(
                config, event=f"data: {last_payload}\n\n", synthetic_query=synthetic_query, job_id=job_id
            )
            await _handle_event(config, event="data: [DONE]\n\n", synthetic_query=synthetic_query, job_id=job_id)
            logger.info(f"✅ Queried node: {node.node_id} for task: {task}. Success: {not first_message}.")

        response_time = time.time() - start_time
        query_result = utility_models.QueryResult(
            formatted_response=text_jsons if len(text_jsons) > 0 else None,
            node_id=node.node_id,
            response_time=response_time,
            task=task,
            success=not first_message,
            node_hotkey=node.hotkey,
            status_code=status_code,
        )
    except Exception as e:
        logger.error(
            f"Unexpected exception when querying node: {node.node_id} for task: {task}. Payload: {payload}. Error: {e}"
        )
        query_result = construct_500_query_result(node, task)
    finally:
        await utils.adjust_contender_from_result(config, query_result, contender, synthetic_query, payload=payload)
        await config.redis_db.expire(rcst.QUERY_RESULTS_KEY + ":" + job_id, 10)


async def query_node_stream(config: Config, contender: Contender, node: Node, payload: dict):
    address = client.construct_server_address(
        node,
        replace_with_docker_localhost=config.replace_with_docker_localhost,
        replace_with_localhost=config.replace_with_localhost,
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

