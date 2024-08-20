import asyncio
import json
from redis.asyncio import Redis
from validator.models import Contender
from validator.query_node.src.query_config import Config
from core.tasks import Task
from core import tasks_config as tcfg
from validator.utils import contender_utils as putils
from core.logging import get_logger
from validator.utils import redis_constants as rcst, redis_dataclasses as rdc
from validator.query_node.src import query
from validator.db.src.sql.contenders import get_contenders_for_task
from validator.db.src.sql.nodes import get_node

logger = get_logger(__name__)

MAX_CONCURRENT_TASKS = 1


async def _decrement_requests_remaining(redis_db: Redis, task: Task):
    key = f"task_synthetics_info:{task.value}:requests_remaining"
    await redis_db.decr(key)


async def _handle_stream_query(
    config: Config, message: rdc.QueryQueueMessage, contenders_to_query: list[Contender]
) -> bool:
    success = False
    for contender in contenders_to_query:
        node = await get_node(config.psql_db, contender.node_id, config.netuid)
        generator = await query.query_node_stream(
            config=config, contender=contender, payload=message.query_payload, node=node
        )

        await query.consume_generator(
            config=config,
            generator=generator,
            job_id=message.job_id,
            synthetic_query=message.query_type == "synthetic",
            contender=contender,
            node=node,
            payload=message.query_payload,
        )
        if generator is None:
            continue
        else:
            success = True

    return success


async def _handle_nonstream_query(
    config: Config, message: rdc.QueryQueueMessage, contenders_to_query: list[Contender]
) -> bool:
    success = False
    for contender in contenders_to_query:
        node = await get_node(config.psql_db, contender.node_id, config.netuid)
        generator = await query.query_node_stream(
            config=config, contender=contender, payload=message.query_payload, node=node
        )


            success = True

    return success


async def process_task(config: Config, message: rdc.QueryQueueMessage):
    task = Task(message.task)

    if message.query_type == "organic":
        await _decrement_requests_remaining(config.redis_db, task)
    else:
        message.query_payload = await putils.get_synthetic_payload(config.redis_db, task)

    stream = tcfg.TASK_TO_CONFIG[task].is_stream

    async with await config.psql_db.connection() as connection:
        contenders_to_query = await get_contenders_for_task(connection, task)

    if contenders_to_query is None:
        raise ValueError("No contenders to query! :(")

    if stream:
        return _handle_stream_query(config, message, contenders_to_query)
    else:
        return _handle_nonstream_query(config, message, contenders_to_query)


async def listen_for_tasks(config: Config):
    tasks: set[asyncio.Task] = set()

    logger.info("Listening for tasks.")
    while True:
        done = {t for t in tasks if t.done()}
        tasks.difference_update(done)
        for t in done:
            await t

        while len(tasks) < MAX_CONCURRENT_TASKS:
            message_json = await config.redis_db.blpop(rcst.QUERY_QUEUE_KEY, timeout=1)
            if not message_json:
                break
            task = asyncio.create_task(process_task(config, rdc.QueryQueueMessage(**json.loads(message_json[1]))))
            tasks.add(task)

        await asyncio.sleep(0.01)
