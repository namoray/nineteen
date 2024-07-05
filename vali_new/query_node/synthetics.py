import asyncio


from redis.asyncio import Redis
from core import Task
from vali_new.models import Participant
from vali_new.utils import participant_utils as putils, synthetic_utils as sutils, query_utils as qutils
from vali_new.utils import redis_constants as rcst
from vali_new.query_node import utils
from core import bittensor_overrides as bto


async def execute_query_when_available(redis_db: Redis, dendrite: bto.dendrite, timeout: float = 0) -> None:
    # Does this need to be async, if it's in it's own asyncio task?
    participant_id = redis_db.blpop(keys=[rcst.SYNTHETIC_DATA_KEY])
    participant = await putils.load_participant(redis_db, participant_id)

    asyncio.create_task(execute_synthetic_query(redis_db, participant.hotkey, participant.task, dendrite))


async def monitor_for_queries(redis_db: Redis, dendrite: bto.dendrite):
    while True:
        await execute_query_when_available(redis_db, dendrite, timeout=0)


async def execute_synthetic_query(redis_db: Redis, participant: Participant, task: Task, dendrite: bto.dendrite):
    synthetic_synapse = await sutils.fetch_synthetic_data_for_task(redis_db, task)
    stream = task in [Task.chat_llama_3, Task.chat_mixtral]
    if stream:
        # TODO: Need to update uid queue here
        generator = utils.query_miner_stream(participant, synthetic_synapse, task, dendrite, synthetic_query=True)
        # TODO: Log this somewhere so we can see details about every request that is happening.
        # Probably a job for prom and grafana? or redis and grafana

        # We need to iterate through the generator to consume it - so the request finishes
        asyncio.create_task(qutils.consume_generator(generator))
    else:
        return
        # asyncio.create_task(
        #     utils.query_miner_no_stream(
        #         uid_record, synthetic_synapse, outgoing_model, task, dendrite, synthetic_query=True
        #     )
        # )


async def main():
    redis_db = Redis()
    await monitor_for_queries(redis_db)


if __name__ == "__main__":
    asyncio.run(main())
