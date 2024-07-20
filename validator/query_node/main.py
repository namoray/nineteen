import asyncio
import json
import os
from redis.asyncio import Redis
from core import Task, bittensor_overrides as bt
from validator.db.database import PSQLDB
from validator.utils import participant_utils as putils, synthetic_utils as sutils, query_utils as qutils
from validator.utils import redis_constants as rcst
from validator.query_node import utils
from core.logging import get_logger

logger = get_logger(__name__)

DEBUG = os.getenv("ENV", "prod") != "prod"
JOB_TIMEOUT = 300


async def process_job(redis_db: Redis, psql_db: PSQLDB, dendrite: bt.dendrite, job_data):
    # Add separate handling for organics and synthetics
    participant_id = job_data["participant_id"]
    participant = await putils.load_participant(psql_db, participant_id)

    await redis_db.hset(f"job:{participant_id}", "state", "processing")

    try:
        synthetic_synapse = await sutils.fetch_synthetic_data_for_task(redis_db, participant.task)
        stream = participant.task in [Task.chat_llama_3, Task.chat_mixtral]

        if stream:
            generator = utils.query_miner_stream(
                participant, synthetic_synapse, participant.task, dendrite, synthetic_query=True, debug=DEBUG
            )
            await qutils.consume_generator(generator)

        await redis_db.hset(f"job:{participant_id}", "state", "completed")
        logger.info(f"Job {participant_id} completed successfully")
    except Exception as e:
        logger.error(f"Job {participant_id} failed: {str(e)}")
        await redis_db.hset(f"job:{participant_id}", "state", "failed")
        await redis_db.hset(f"job:{participant_id}", "error", str(e))


async def process_job_with_timeout(redis_db: Redis, psql_db: PSQLDB, dendrite: bt.dendrite, job_data):
    try:
        await asyncio.wait_for(process_job(redis_db, psql_db, dendrite, job_data), timeout=JOB_TIMEOUT)
    except asyncio.TimeoutError:
        participant_id = job_data["participant_id"]
        logger.error(f"Job {participant_id} timed out after {JOB_TIMEOUT} seconds")
        await redis_db.hset(f"job:{participant_id}", "state", "timeout")
        await redis_db.hset(f"job:{participant_id}", "error", f"Job timed out after {JOB_TIMEOUT} seconds")


async def worker_loop(redis_db: Redis, psql_db: PSQLDB, dendrite: bt.dendrite, queue_name, max_concurrent_jobs=100):
    active_tasks: set[asyncio.Task] = set()
    while True:
        try:
            active_tasks = {task for task in active_tasks if not task.done()}

            while len(active_tasks) >= max_concurrent_jobs:
                done, _ = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    try:
                        await task
                    except Exception as e:
                        logger.error(f"Task failed with error: {str(e)}")
                active_tasks = {task for task in active_tasks if not task.done()}

            _, job = await redis_db.blpop(queue_name)
            job_data = json.loads(job)

            task = asyncio.create_task(process_job_with_timeout(redis_db, psql_db, dendrite, job_data))
            active_tasks.add(task)
            task.add_done_callback(lambda t: active_tasks.discard(t))

        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            await asyncio.sleep(1)


async def heartbeat(redis_db: Redis):
    while True:
        logger.debug("Worker heartbeat")
        await redis_db.set("worker_heartbeat", "alive", ex=10)
        await asyncio.sleep(5)


async def run_worker(redis_db: Redis, psql_db: PSQLDB, dendrite: bt.dendrite, queue_name):
    logger.debug("Starting worker")
    try:
        heartbeat_task = asyncio.create_task(heartbeat(redis_db))
        await asyncio.gather(worker_loop(redis_db, psql_db, dendrite, queue_name), heartbeat_task)
    except asyncio.CancelledError:
        logger.info("Worker cancelled")
    except Exception as e:
        logger.error(f"Unexpected error in worker: {str(e)}")
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


async def main():
    redis_db = Redis(host="redis")
    psql_db = PSQLDB()
    await psql_db.connect()
    dendrite = bt.dendrite()
    logger.warning("Starting worker")
    queue_name = rcst.SYNTHETIC_DATA_KEY
    await run_worker(redis_db, psql_db, dendrite, queue_name)


if __name__ == "__main__":
    asyncio.run(main())
