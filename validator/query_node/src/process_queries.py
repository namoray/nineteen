from redis.asyncio import Redis
from core.models.payload_models import TextToImageResponse
from validator.models import Contender
from validator.query_node.src.query_config import Config
from core.tasks import Task
from core import tasks_config as tcfg
from validator.utils import contender_utils as putils
from core.logging import get_logger
from validator.utils import redis_dataclasses as rdc
from validator.query_node.src.query import stream, nonstream
from validator.db.src.sql.contenders import get_contenders_for_task
from validator.db.src.sql.nodes import get_node
from validator.utils import generic_constants as gcst
logger = get_logger(__name__)

MAX_CONCURRENT_TASKS = 1


async def _decrement_requests_remaining(redis_db: Redis, task: Task):
    key = f"task_synthetics_info:{task.value}:requests_remaining"
    await redis_db.decr(key)

async def _acknowledge_job(redis_db: Redis, job_id: str):
    logger.debug(f"Acknlowedging job id : {job_id}")
    await redis_db.publish(f"{gcst.ACKNLOWEDGED}:{job_id}", "acknowledged")
    
async def _handle_stream_query(
    config: Config, message: rdc.QueryQueueMessage, contenders_to_query: list[Contender]
) -> bool:
    success = False
    for contender in contenders_to_query:
        node = await get_node(config.psql_db, contender.node_id, config.netuid)
        generator = await stream.query_node_stream(
            config=config, contender=contender, payload=message.query_payload, node=node
        )

        await stream.consume_generator(
            config=config,
            generator=generator,
            job_id=message.job_id,
            synthetic_query=message.query_type == gcst.SYNTHETIC,
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
        await nonstream.query_nonstream(
            config=config,
            contender=contender,
            node=node,
            payload=message.query_payload,
            response_model=TextToImageResponse,
            synthetic_query=message.query_type == gcst.SYNTHETIC,
        )

    return success





async def process_task(config: Config, message: rdc.QueryQueueMessage):
    task = Task(message.task)

    if message.query_type == gcst.ORGANIC:
        await _acknowledge_job(config.redis_db, message.job_id)
        await _decrement_requests_remaining(config.redis_db, task)
    else:
        message.query_payload = await putils.get_synthetic_payload(config.redis_db, task)

    stream = tcfg.TASK_TO_CONFIG[task].is_stream

    async with await config.psql_db.connection() as connection:
        contenders_to_query = await get_contenders_for_task(connection, task)

    if contenders_to_query is None:
        raise ValueError("No contenders to query! :(")

    if stream:
        return await _handle_stream_query(config, message, contenders_to_query)
    else:
        return await _handle_nonstream_query(config=config, message=message, contenders_to_query=contenders_to_query)
