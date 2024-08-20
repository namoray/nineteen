import time
from httpx import Response
from pydantic import BaseModel, ValidationError
from core.models import utility_models
from core.tasks import Task
from validator.query_node.src.query_config import Config

from validator.models import Contender
from fiber.chain_interactions.models import Node
from fiber.validator import client
from core import tasks_config as tcfg
from fiber.logging_utils import get_logger
from validator.query_node.src import utils

logger = get_logger(__name__)


def get_formatted_response(
    response: Response,
    response_model: BaseModel,
) -> BaseModel | None:
    if response and response.status_code == 200:
        formatted_response = _extract_response(response, response_model)
        return formatted_response
    else:
        return None


def _extract_response(response: Response, response_model: BaseModel) -> BaseModel | None:
    try:
        formatted_response = response_model(**response.json())

        # If we're expecting a result (i.e. not nsfw), then try to deserialize
        if (hasattr(formatted_response, "is_nsfw") and not formatted_response.is_nsfw) or not hasattr(
            formatted_response, "is_nsfw"
        ):
            if hasattr(formatted_response, "image_b64"):
                assert formatted_response.image_b64 != ""

        return formatted_response
    except ValidationError as e:
        logger.debug(f"Failed to deserialize for some reason: {e}")
        return None


async def query_nonstream(
    config: Config, contender: Contender, node: Node, payload: dict, response_model: BaseModel, synthetic_query: bool
) -> utility_models.QueryResult:
    node_uid = contender.node_hotkey
    node_id = contender.node_id

    time_before_query = time.time()
    response = await client.make_non_streamed_post(
        httpx_client=config.httpx_client,
        server_address=client.construct_server_address(
            node,
            replace_with_docker_localhost=config.replace_with_docker_localhost,
            replace_with_localhost=config.replace_with_localhost,
        ),
        validator_ss58_address=config.ss58_address,
        fernet=node.fernet,
        symmetric_key_uuid=node.symmetric_key_uuid,
        endpoint=tcfg.TASK_TO_CONFIG[Task(contender.task)].endpoint,
        payload=payload,
        timeout=tcfg.TASK_TO_CONFIG[Task(contender.task)].timeout,
    )
    response_time = time.time() - time_before_query

    formatted_response = get_formatted_response(response, response_model)
    if formatted_response is not None:
        logger.info(f"✅ Successfully queried node: {node_uid} for task: {contender.task}")
        query_result = utility_models.QueryResult(
            formatted_response=formatted_response,
            node_uid=node_uid,
            response_time=response_time,
            task=contender.task,
            node_hotkey=contender.node_hotkey,
            status_code=response.status_code,
            success=True,
        )
        # create_scoring_adjustment_task(query_result, synapse, contender, synthetic_query)
        return query_result
    else:
        query_result = utility_models.QueryResult(
            formatted_response=None,
            node_uid=node_uid,
            response_time=None,
            task=contender.task,
            status_code=response.status_code,
            success=False,
            node_hotkey=contender.node_hotkey,
        )

    await utils.adjust_contender_from_result(
        config=config, query_result=query_result, contender=contender, synthetic_query=synthetic_query, payload=payload
    )
    return query_result
