import asyncio
import collections
import random
from typing import Dict, List

from core import Task
from vali_new.models import Participant
from validation.models import UidRecordsForTask
from core import tasks
from validation.proxy.utils import query_utils
from validation.db.db_management import db_manager
from vali_new.utils import redis_constants as rcst
from vali_new.utils import redis_utils as rutils
from redis.asyncio import Redis


def calculate_period_scores_for_uids(uid_records_for_tasks: UidRecordsForTask) -> None:
    for task in uid_records_for_tasks:
        for record in uid_records_for_tasks[task].values():
            record.calculate_period_score()


async def store_period_scores(uid_records_for_tasks: UidRecordsForTask, validator_hotkey: str) -> None:
    for uid_records in uid_records_for_tasks.values():
        for uid_record in uid_records.values():
            await db_manager.insert_uid_record(uid_record, validator_hotkey)


def _get_percentage_of_tasks_to_score():
    return 1

async def load_participant(redis_db: Redis, participant_id: str) -> Participant:
    participant_raw = await rutils.json_load_from_redis(redis_db, participant_id)
    participant = Participant(**participant_raw)
    return participant


async def load_participants(redis_db: Redis) -> List[Participant]:
    participant_ids_set = await redis_db.smembers(rcst.PARTICIPANT_IDS_KEY)

    participants = []
    for participant_id in (i.decode("utf-8") for i in participant_ids_set):
        participants.append(await load_participant(redis_db, participant_id))

    return participants


async def handle_task_scoring_for_uid(
    redis_db: Redis,
    participant_id: Participant
) -> None:
    """
    Calculates volume to score
    Calculates number of synthetic requests off the back of that
    Creates a uid record & stores it
    Calculates delay between requests

    Add a marker to redis between the delays to send a request
    """


    i = 0

    # Is there a better way to do this than at the start?
    participant = await load_participant(redis_db, participant_id)
    while participant.synthetic_requests_still_to_make > 0:
        # Random perturbation(s) to make sure we dont burst all requests at once
        if i == 0:
            random_factor = random.random()
        else:
            random_factor = random.random() * 0.05 + 0.95

        await asyncio.sleep(participant.delay_between_synthetic_requests * random_factor)

        participant = await load_participant(redis_db, participant_id)
        await rutils.add_str_to_redis_list(redis_db, rcst.SYNTHETIC_QUERIES_TO_MAKE_KEY, participant.id)

        # Organic queries consume volume too, so it's possible we enough that we don't
        # Need synthetics anymore. This is the only fresh info we need from 'participant' object
        if await rutils.check_value_is_in_set(redis_db, rcst.PARITICIPANT_IDS_TO_STOP_KEY, participant.id):
            await rutils.remove_value_from_set(redis_db, rcst.PARITICIPANT_IDS_TO_STOP_KEY, participant.id)
            break


async def start_synthetic_scoring(
    redis_db: Redis,
) -> None:
    synthetic_scoring_tasks = []
    participants = await load_participants(redis_db) 

    for participant in participants:
        synthetic_scoring_tasks.append(
            asyncio.create_task(
                handle_task_scoring_for_uid(
                    redis_db,
                    participant
                )
            )
        )
    return synthetic_scoring_tasks


class UidManager:
    def __init__(
        self,
        redis_db: Redis,
    ) -> None:
        self.redis_db = redis_db
        # Replace with redis?
        self.uid_records_for_tasks: UidRecordsForTask = collections.defaultdict(dict)
        self.synthetic_scoring_tasks: List[asyncio.Task] = []
        self.task_to_hotkey_queue: Dict[Task, query_utils.UIDQueue] = {}

    async def collect_synthetic_scoring_results(self) -> None:
        await asyncio.gather(*self.synthetic_scoring_tasks)

    async def start_period(self) -> None:
        # Get the participant info from redis

        # Store each participant info in redis somehow
        ...


async def main():
    redis_db = Redis()
    uid_manager = UidManager(
        capacities_for_tasks={tasks.Task.chat_mixtral: {1: 1_000_000}},
        validator_hotkey="123",
        is_testnet=True,
        redis_db=redis_db,
    )

    def patched_percentage_tasks_to_score():
        return 1

    uid_manager._get_percentage_of_tasks_to_score = patched_percentage_tasks_to_score
    await uid_manager.start_synthetic_scoring()
    await uid_manager.collect_synthetic_scoring_results()


if __name__ == "__main__":
    asyncio.run(main())
