import json
import time
from asyncpg import Connection
from redis.asyncio import Redis
from core.models.payload_models import ImageResponse
from validator.db.src.sql.weights import get_latest_scoring_stats_for_contenders
from validator.models import Contender
from validator.query_node.src.query_config import Config
from core import task_config as tcfg
from validator.utils.generic import generic_utils as gutils
from validator.utils.contender import contender_utils as putils
from validator.utils.redis import redis_constants as rcst
from fiber.logging_utils import get_logger
from validator.utils.redis import redis_dataclasses as rdc
from validator.query_node.src.query import nonstream, streaming
from validator.db.src.sql.contenders import get_contenders_for_task
from validator.db.src.sql.nodes import get_node
from validator.utils.generic import generic_constants as gcst

logger = get_logger(__name__)

MAX_CONCURRENT_TASKS = 10
CONTENDERS_PER_TASK = 5


async def _decrement_requests_remaining(redis_db: Redis, task: str):
    key = f"task_synthetics_info:{task}:requests_remaining"
    await redis_db.decr(key)


async def _acknowledge_job(redis_db: Redis, job_id: str):
    logger.debug(f"Acknowledging job id : {job_id}")
    await redis_db.publish(f"{gcst.ACKNLOWEDGED}:{job_id}", json.dumps({gcst.ACKNLOWEDGED: True}))


async def _handle_stream_query(config: Config, message: rdc.QueryQueueMessage, contenders_to_query: list[Contender]) -> bool:
    success = False
    for contender in contenders_to_query[:5]:
        node = await get_node(config.psql_db, contender.node_id, config.netuid)
        if node is None:
            logger.error(f"Node {contender.node_id} not found in database for netuid {config.netuid}")
            continue
        logger.debug(f"Querying node {contender.node_id} for task {contender.task} with payload: {message.query_payload}")
        start_time = time.time()
        generator = await streaming.query_node_stream(
            config=config, contender=contender, payload=message.query_payload, node=node
        )

        # TODO: Make sure we still punish if generator is None
        if generator is None:
            continue

        success = await streaming.consume_generator(
            config=config,
            generator=generator,
            job_id=message.job_id,
            synthetic_query=message.query_type == gcst.SYNTHETIC,
            contender=contender,
            node=node,
            payload=message.query_payload,
            start_time=start_time,
        )
        if success:
            break

    if not success:
        logger.error(
            f"All Contenders {[contender.node_id for contender in contenders_to_query]} for task {message.task} failed to respond! :("
        )
        await _handle_error(
            config=config,
            synthetic_query=message.query_type == gcst.SYNTHETIC,
            job_id=message.job_id,
            status_code=500,
            error_message=f"Service for task {message.task} is not responding, please try again",
        )
    return success


async def _handle_nonstream_query(config: Config, message: rdc.QueryQueueMessage, contenders_to_query: list[Contender]) -> bool:
    success = False
    for contender in contenders_to_query:
        node = await get_node(config.psql_db, contender.node_id, config.netuid)
        if node is None:
            logger.error(f"Node {contender.node_id} not found in database for netuid {config.netuid}")
            continue
        success = await nonstream.query_nonstream(
            config=config,
            contender=contender,
            node=node,
            payload=message.query_payload,
            response_model=ImageResponse,
            synthetic_query=message.query_type == gcst.SYNTHETIC,
            job_id=message.job_id,
        )
        if success:
            break

    if not success:
        logger.error(
            f"All Contenders {[contender.node_id for contender in contenders_to_query]} for task {message.task} failed to respond! :("
        )
        await _handle_error(
            config=config,
            synthetic_query=message.query_type == gcst.SYNTHETIC,
            job_id=message.job_id,
            status_code=500,
            error_message=f"Service for task {message.task} is not responding, please try again",
        )
    return success


async def _handle_error(config: Config, synthetic_query: bool, job_id: str, status_code: int, error_message: str) -> None:
    if not synthetic_query:
        await config.redis_db.publish(
            f"{rcst.JOB_RESULTS}:{job_id}",
            gutils.get_error_event(job_id=job_id, error_message=error_message, status_code=status_code),
        )


async def process_task(config: Config, message: rdc.QueryQueueMessage):
    task = message.task

    if message.query_type == gcst.ORGANIC:
        logger.debug(f"Acknowledging job id : {message.job_id}")
        await _acknowledge_job(config.redis_db, message.job_id)
        logger.debug(f"Successfully acknowledged job id : {message.job_id} ✅")
        await _decrement_requests_remaining(config.redis_db, task)
    else:
        message.query_payload = await putils.get_synthetic_payload(config.redis_db, task)

    task_config = tcfg.get_enabled_task_config(task)
    if task_config is None:
        logger.error(f"Can't find the task {task} in the query node!")
        await _handle_error(
            config=config,
            synthetic_query=message.query_type == gcst.SYNTHETIC,
            job_id=message.job_id,
            status_code=500,
            error_message=f"Can't find the task {task}, please try again later",
        )
        return

    stream = task_config.is_stream

    async with await config.psql_db.connection() as connection:
        contenders_for_task = await get_contenders_for_task(connection, task, top_x=CONTENDERS_PER_TASK * 2)
        if message.query_type == gcst.ORGANIC:
            contenders_to_query = await _prioritise_contenders_by_scoring_stats(connection, task, contenders_for_task)
        else:
            contenders_to_query = contenders_for_task[:CONTENDERS_PER_TASK]

    if contenders_to_query is None:
        raise ValueError("No contenders to query! :(")

    try:
        if stream:
            return await _handle_stream_query(config, message, contenders_to_query)
        else:
            return await _handle_nonstream_query(config=config, message=message, contenders_to_query=contenders_to_query)
    except Exception as e:
        logger.error(f"Error processing task {task}: {e}")
        await _handle_error(
            config=config,
            synthetic_query=message.query_type == gcst.SYNTHETIC,
            job_id=message.job_id,
            status_code=500,
            error_message=f"Error processing task {task}: {e}",
        )


async def _prioritise_contenders_by_scoring_stats(
        connection: Connection, task: str, contenders: list[Contender], top_x: int = CONTENDERS_PER_TASK
)-> list[Contender]:
    scoring_stats = await get_latest_scoring_stats_for_contenders(connection, task, contenders)
    scoring_stats_by_contender = {ss.miner_hotkey: ss for ss in scoring_stats}
    contenders_with_combined_scores = []

    for contender in contenders:
        contender_scoring_stats = scoring_stats_by_contender.get(contender.node_hotkey)
        contender_scoring_stats_score = contender_scoring_stats.normalised_net_score if contender_scoring_stats else 0
        combined_score = await _combine_current_score_with_scoring_stats(
            contender.total_requests_made, contender_scoring_stats_score
        )
        contenders_with_combined_scores.append((contender, combined_score))

    sorted_contenders_with_combined_scores = sorted(contenders_with_combined_scores, key=lambda tup: tup[1], reverse=True)

    return [sc[0] for sc in sorted_contenders_with_combined_scores[:top_x]]


async def _combine_current_score_with_scoring_stats(current_score: float, scoring_stats_score: float) -> float:
    weight_current = 0.6
    weight_stats = 0.4

    return (current_score * weight_current + scoring_stats_score * weight_stats) / (weight_current + weight_stats)
