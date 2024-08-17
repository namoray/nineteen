from core.tasks import Task
from validator.query_node.src.query_config import Config
from validator.models import Contender
from fiber.validator import client
from fiber.validator.client import Node
from core import tasks_config as tcfg


async def query_node_stream(config: Config, contender: Contender, node: Node, payload: dict):
    return await client.make_streamed_post(
        httpx_client=config.httpx_client,
        server_address=client.construct_server_address(node),
        validator_ss58_address=config.validator_ss58_address,
        fernet=node.fernet,
        key_uuid=node.symmetric_key_uuid,
        payload=payload,
        endpoint=tcfg.TASK_TO_CONFIG[Task(contender.task)].endpoint,
        timeout=tcfg.TASK_TO_CONFIG[Task(contender.task)].timeout,
    )


async def get_contenders_to_query(config: Config, task: Task) -> list[Contender]: ...
