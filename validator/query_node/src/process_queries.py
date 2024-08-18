import asyncio
import json
from redis.asyncio import Redis
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


async def process_task(config: Config, message: rdc.QueryQueueMessage):
    task = Task(message.task)

    if message.query_type == "organic":
        await _decrement_requests_remaining(config.redis_db, task)
    else:
        message.query_payload = await putils.get_synthetic_payload(config.redis_db, task)

    stream = tcfg.TASK_TO_CONFIG[task].is_stream

    if stream:
        # Decide which contenders to query.
        async with await config.psql_db.connection() as connection:
            contenders_to_query = await get_contenders_for_task(connection, task)

        logger.debug(f"Contenders: {contenders_to_query}")
        # Query em
        for contender in contenders_to_query:
            node = await get_node(config.psql_db, contender.node_id, config.netuid)
            logger.debug(f"Node: {node}")
            generator = await query.query_node_stream(
                config=config, contender=contender, payload=message.query_payload, node=node
            )

            await query.consume_generator(
                config.redis_db, generator, synthetic_query=message.query_payload.get("synthetic_query"), job_id=message.job_id
            )
            # If fails straight away, then go again , else break
            if True:
                break
    else:
        # Handle non-stream tasks here
        pass


async def listen_for_tasks(config: Config):
    ongoing_tasks = set()

    logger.info("Listening for tasks...")

    async def process_and_remove(message: rdc.QueryQueueMessage):
        try:
            await process_task(config, message)
        finally:
            ongoing_tasks.remove(message.job_id)

    while True:
        logger.debug(f"Ongoing tasks: {ongoing_tasks}, length: {len(ongoing_tasks)}, max: {MAX_CONCURRENT_TASKS}")
        if len(ongoing_tasks) < MAX_CONCURRENT_TASKS:
            message_json = await config.redis_db.lpop(rcst.QUERY_QUEUE_KEY)
            if message_json:
                message = rdc.QueryQueueMessage(**json.loads(message_json))
                ongoing_tasks.add(message.job_id)
                asyncio.create_task(process_and_remove(message))
            else:
                await asyncio.sleep(0.1)
        else:
            await asyncio.sleep(1)
