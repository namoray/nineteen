import json
from validator.db import sql
from validator.db.database import PSQLDB
from validator.models import Participant
from validator.utils import redis_constants as rcst
from validator.utils import redis_utils as rutils
from redis.asyncio import Redis
from core.logging import get_logger

from asyncpg import Connection

logger = get_logger(__name__)


def construct_synthetic_query_message(participant_id: str) -> str:
    return json.dumps({"query_type": "synthetic", "query_payload": {"participant_id": participant_id}})


# Consistently about 1ms
async def load_participant(psql_db: PSQLDB, participant_id: str) -> Participant | None:
    async with await psql_db.connection() as connection:
        return await sql.fetch_participant(connection, participant_id)


async def load_participants(psql_db: PSQLDB) -> list[Participant]:
    async with await psql_db.connection() as connection:
        return await sql.fetch_all_participants(connection)


# TODO: Might be able to get rid of it now
async def check_and_remove_participant_from_synthetics_if_finished(redis_db: Redis, participant_id: str) -> bool:
    if await rutils.check_value_is_in_set(redis_db, rcst.PARITICIPANT_IDS_TO_STOP_KEY, participant_id):
        logger.debug(f"Removing {participant_id} from synthetic queries")
        await rutils.remove_value_from_set(redis_db, rcst.PARITICIPANT_IDS_TO_STOP_KEY, participant_id)
        return True
    return False


async def add_synthetic_query_to_queue(redis_db: Redis, participant_id: str) -> None:
    message = construct_synthetic_query_message(participant_id)
    await rutils.add_str_to_redis_list(redis_db, rcst.QUERY_QUEUE_KEY, message)


async def load_query_queue(redis_db: Redis) -> list[str]:
    return await rutils.get_redis_list(redis_db, rcst.QUERY_QUEUE_KEY)


async def load_synthetic_scheduling_queue(redis_db: Redis) -> list[str]:
    return await rutils.get_sorted_set(redis_db, rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY)


def calculate_period_score(participant: Participant) -> float:
    """
    Calculate a period score (not including quality which is scored separately)

    The closer we are to max volume used, the more forgiving we can be.
    For example, if you rate limited me loads (429), but I got most of your volume,
    then fair enough, perhaps I was querying too much

    But if I barely queried your volume, and you still rate limited me loads (429),
    then you're very naughty, you.
    """
    if participant.total_requests_made == 0 or participant.capacity == 0:
        return None

    participant.capacity = max(participant.capacity, 1)
    volume_unqueried = max(participant.capacity - participant.consumed_capacity, 0)

    percentage_of_volume_unqueried = volume_unqueried / participant.capacity
    percentage_of_429s = participant.requests_429 / participant.total_requests_made
    percentage_of_500s = participant.requests_500 / participant.total_requests_made
    percentage_of_good_requests = (
        participant.total_requests_made - participant.requests_429 - participant.requests_500
    ) / participant.total_requests_made

    # NOTE: Punish rate limit slightly less, to encourage only completing that which you can do
    rate_limit_punishment_factor = percentage_of_429s**2 * percentage_of_volume_unqueried
    server_error_punishment_factor = percentage_of_500s * percentage_of_volume_unqueried

    period_score = max(
        percentage_of_good_requests * (1 - rate_limit_punishment_factor) * (1 - server_error_punishment_factor), 0
    )

    return period_score

async def add_period_scores_to_current_participants(connection: Connection) -> None:
    participants = await sql.fetch_all_participants(connection, None)
    for participant in participants:
        period_score = calculate_period_score(participant)
        participant.period_score = period_score

    await sql.update_participants_period_scores(connection, participants)