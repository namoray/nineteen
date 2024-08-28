from redis.asyncio import Redis
from validator.utils import redis_constants as rcst
import asyncio



# Function to handle messages from the channel
async def handle_messages(pubsub):
    async for message in pubsub.listen():
        print(message)
        if message['type'] == 'message':
            print(f"Received message: {message}")

# Start listening for messages in the background
async def main():
    redis = Redis(host="localhost", port=6379, db=0)
    # Subscribe to the 'JOB_RESULTS_TEST' channel
    pubsub = redis.pubsub()
    await pubsub.subscribe(f'{rcst.JOB_RESULTS}:TEST')

    await handle_messages(pubsub)

if __name__ == "__main__":
    asyncio.run(main())

    