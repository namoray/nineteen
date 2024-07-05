import asyncio
import random

from vali_new.models import Participant
from vali_new.utils import redis_constants as rcst
from vali_new.utils import redis_utils as rutils
from redis.asyncio import Redis
from vali_new.utils import participant_utils as putils

async def handle_scheduling_for_participant(redis_db: Redis, participant_id: Participant) -> None:
    """
    Calculates volume to score
    Calculates number of synthetic requests off the back of that
    Creates a uid record & stores it
    Calculates delay between requests

    Add a marker to redis between the delays to send a request
    """
    i = 0

    # Is there a better way to do this than at the start?
    participant = await putils.load_participant(redis_db, participant_id)
    while participant.synthetic_requests_still_to_make > 0:
        # Random perturbation(s) to make sure we dont burst all requests at once
        if i == 0:
            random_factor = random.random()
        else:
            random_factor = random.random() * 0.05 + 0.95

        await asyncio.sleep(participant.delay_between_synthetic_requests * random_factor)

        participant = await putils.load_participant(redis_db, participant_id)
        await rutils.add_str_to_redis_list(redis_db, rcst.SYNTHETIC_QUERIES_TO_MAKE_KEY, participant.id)

        # Organic queries consume volume too, so it's possible we enough that we don't
        # Need synthetics anymore. This is the only fresh info we need from 'participant' object
        if await rutils.check_value_is_in_set(redis_db, rcst.PARITICIPANT_IDS_TO_STOP_KEY, participant.id):
            await rutils.remove_value_from_set(redis_db, rcst.PARITICIPANT_IDS_TO_STOP_KEY, participant.id)
            break


async def start_scheduling(
    redis_db: Redis,
) -> None:
    synthetic_scoring_tasks = []
    participants = await putils.load_participants(redis_db)

    for participant in participants:
        synthetic_scoring_tasks.append(asyncio.create_task(handle_scheduling_for_participant(redis_db, participant)))
    return synthetic_scoring_tasks


async def main():
    redis_db = Redis()

    scoring_tasks = await start_scheduling(redis_db)
    await asyncio.gather(*scoring_tasks)


if __name__ == "__main__":
    asyncio.run(main())
