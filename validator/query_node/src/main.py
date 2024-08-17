import asyncio
import json
from redis.asyncio import Redis
from validator.control_node.src.control_config import Config
from core.tasks import Task
from core import tasks_config as tcfg
from validator.utils import contender_utils as putils
from validator.utils import query_utils as qutils
from core.logging import get_logger
from validator.utils import redis_constants as rcst, redis_dataclasses as rdc
from validator.query_node.src import query
logger = get_logger(__name__)

MAX_CONCURRENT_TASKS = 100



async def process_task(config: Config, message: rdc.QueryQueueMessage):
    task = Task(message.task)

    if message.query_type == "organic":
        await decrement_requests_remaining(config.redis_db, task)
    else:
        message.query_payload = await putils.get_synthetic_synapse(config.psql_db, task)


    stream = tcfg.TASK_TO_CONFIG[task].is_stream


    if stream:
        # Decide which contenders to query. 
        contenders_to_query = await query.get_contenders_to_query(config, task)

        # Query em
        for contender in contenders_to_query:
            generator = query.query_node_stream(
                config=config,
                task=task,
                contender=contender,

            )

            await qutils.consume_generator(
                config.redis_db, generator, synthetic_query=message.query_payload.get("synthetic_query")
            )
            # If fails straight away, then go again , else break
            if True:
                break


    else:
        # Handle non-stream tasks here
        pass


async def decrement_requests_remaining(redis_db: Redis, task: Task):
    key = f"task_synthetics_info:{task.value}:requests_remaining"
    await redis_db.decr(key)


async def listen_for_tasks(config: Config):
    ongoing_tasks = set()

    async def process_and_remove(message):
        try:
            await process_task(config, message)
        finally:
            ongoing_tasks.remove(message)

    while True:
        if len(ongoing_tasks) < MAX_CONCURRENT_TASKS:
            message_json = await config.redis_db.lpop(rcst.QUERY_QUEUE_KEY)
            if message_json:
                message = QueryQueueMessage(**json.loads(message_json))
                ongoing_tasks.add(message)
                asyncio.create_task(process_and_remove(message))
            else:
                await asyncio.sleep(0.1)  # Short sleep if no messages
        else:
            await asyncio.sleep(0.1)  # Wait a bit before checking again
