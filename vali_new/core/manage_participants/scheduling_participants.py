import asyncio
import random

from redis.asyncio import Redis
from vali_new.utils import participant_utils as putils

from core.logging import get_logger

logger = get_logger(__name__)


async def handle_scheduling_for_participant(redis_db: Redis, participant_id: str) -> None:
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

    logger.debug(f"Scheduling {participant_id}. Delay: {participant.delay_between_synthetic_requests}.")
    while participant.synthetic_requests_still_to_make > 0:
        # Random perturbation(s) to make sure we dont burst all requests at once
        if i == 0:
            random_factor = random.random()
        else:
            random_factor = random.random() * 0.05 + 0.95

        logger.debug(f"Sleeping for {participant.delay_between_synthetic_requests * random_factor} seconds.")
        await asyncio.sleep(participant.delay_between_synthetic_requests * random_factor)

        await putils.add_participant_to_synthetic_query_list(redis_db, participant_id)

        # Organic queries consume volume too, so it's possible we enough that we don't
        # Need synthetics anymore. This is the only fresh info we need from 'participant' object
        finished = putils.check_and_remove_participant_from_synthetics_if_finished(redis_db, participant_id)
        if finished:
            break


async def start_scheduling(
    redis_db: Redis,
) -> None:
    synthetic_scoring_tasks = []
    participants = await putils.load_participants(redis_db)

    for participant in participants:
        synthetic_scoring_tasks.append(asyncio.create_task(handle_scheduling_for_participant(redis_db, participant.id)))
    logger.debug(f"Added {len(synthetic_scoring_tasks)} scheduling tasks")
    return synthetic_scoring_tasks


async def main():
    redis_db = Redis()

    scoring_tasks = await start_scheduling(redis_db)
    await asyncio.gather(*scoring_tasks)


if __name__ == "__main__":
    asyncio.run(main())
