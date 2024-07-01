import asyncio
import json


from redis.asyncio import Redis
from core import Task
from vali_new.utils import redis_utils
from vali_new.utils import redis_constants as rcst
from vali_new import constants as vcst


# TODO: replace this with however pub-sub will work for redis in python
# But ideally we'd be language agnostic for any pub-sub stuff
async def monitor_for_queries(redis_db: Redis):
    while True:
        tasks_in_queue = await redis_utils.json_load_from_redis(
            redis_db, rcst.SYNTHETIC_QUERIES_TO_MAKE_KEY, default=[]
        )
        # THERE must be a better way of doing this, which will also stop two workers getting the same task
        # and trying to pop it too
        if len(tasks_in_queue) > 0:
            task_to_query = json.loads(tasks_in_queue.pop())
            await redis_utils.save_json_to_redis(
                redis_db, rcst.SYNTHETIC_QUERIES_TO_MAKE_KEY, tasks_in_queue, remove_enums=False
            )
            print(task_to_query)
            execute_synthetic_query(redis_db, task_to_query[vcst.HOTKEY_KEY], task_to_query[vcst.TASK_KEY])

        await asyncio.sleep(0.1)


async def execute_synthetic_query(redis_db: Redis, hotkey: str, task: Task):
    print("Task to query:" + task, "hotkey:" + hotkey)


async def main():
    redis_db = Redis()
    await monitor_for_queries(redis_db)


if __name__ == "__main__":
    asyncio.run(main())
