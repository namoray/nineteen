import bittensor as bt
from validation.models import HotkeyRecord
from validation.proxy import work_and_speed_functions
from models import utility_models
from validation.db.db_management import db_manager


async def adjust_uid_record_from_result(
    query_result: utility_models.QueryResult, synapse: bt.Synapse, uid_record: HotkeyRecord, synthetic_query: bool
) -> None:
    """This does a query, and returns either the finished image request"""

    uid_record.total_requests_made += 1

    # Important we dont make the below adjustment here, since we need to make it elsewhere
    # uid_record.synthetic_requests_still_to_make -= 1

    if query_result.status_code == 200 and query_result.success:
        work = work_and_speed_functions.calculate_work(query_result.task, query_result, synapse=synapse.dict())
        uid_record.consumed_volume += work

        await db_manager.potentially_store_result_in_sql_lite_db(
            query_result, query_result.task, synapse, synthetic_query=synthetic_query
        )

    elif query_result.status_code == 429:
        uid_record.requests_429 += 1
    else:
        uid_record.requests_500 += 1
    return query_result
