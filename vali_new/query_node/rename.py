import asyncio


from redis.asyncio import Redis
from vali_new.utils import redis_utils
from vali_new.utils import redis_constants as rcst



# TODO: replace this with however pub-sub will work for redis in python
# But ideally we'd be language agnostic for any pub-sub stuff
async def monitor_for_queries(redis_db: Redis):
    while True:
        tasks_in_queue = await redis_utils.load_json_from_redis(
            redis_db, rcst.SYNTHETIC_QUERIES_TO_MAKE_KEY, default=[]
        )
        # THERE must be a better way of doing this, which will also stop two workers getting the same task 
        # and trying to pop it too
        if len(tasks_in_queue) > 0:
            task_to_query = tasks_in_queue.pop()
            await redis_utils.save_json_to_redis(tasks_in_queue)
        
        print("Task to query:" + task_to_query)
        await asyncio.sleep(0.1)


async def main():
    redis_db = Redis()
    await (monitor_for_queries)


if __name__ == "__main__":
    asyncio.run(main())
