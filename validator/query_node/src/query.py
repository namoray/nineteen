from typing import AsyncGenerator
from core.tasks import Task
from validator.query_node.src.query_config import Config
from validator.models import Contender
from fiber.validator import client
from fiber.chain_interactions.models import Node
from core import tasks_config as tcfg
from validator.utils import redis_constants as rcst

from redis.asyncio import Redis


async def consume_generator(redis_db: Redis, generator: AsyncGenerator, job_id: str, synthetic_query: bool) -> None:
    if synthetic_query:
        async for _ in generator:
            pass
    else:
        assert job_id
        # TODO: Change this to a nicer payload??? what does that mean
        async for text in generator:
            await redis_db.rpush(rcst.QUERY_RESULTS_KEY + ":" + job_id, text)

        await redis_db.expire(rcst.QUERY_RESULTS_KEY + ":" + job_id, 10)


async def query_node_stream(config: Config, contender: Contender, node: Node, payload: dict):
    return  client.make_streamed_post(
        httpx_client=config.httpx_client,
        server_address=client.construct_server_address(node),
        validator_ss58_address=config.ss58_address,
        fernet=node.fernet,
        symmetric_key_uuid=node.symmetric_key_uuid,
        payload=payload,
        endpoint=tcfg.TASK_TO_CONFIG[Task(contender.task)].endpoint,
        timeout=tcfg.TASK_TO_CONFIG[Task(contender.task)].timeout,
    )
