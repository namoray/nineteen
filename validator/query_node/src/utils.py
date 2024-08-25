from core.models import utility_models
from validator.models import Contender
from validator.query_node.src.query_config import Config
from validator.utils import work_and_speed_functions
from core.logging import get_logger
from validator.db.src import functions as db_functions
from validator.db.src.sql.contenders import (
    update_contender_429_count,
    update_contender_500_count,
    update_contender_capacities,
)

logger = get_logger(__name__)


async def adjust_contender_from_result(
    config: Config,
    query_result: utility_models.QueryResult,
    contender: Contender,
    synthetic_query: bool,
    payload: dict,
):
    """
    Update the db with consumed volume
    Store the task result in the db for checking (potentially)

    """

    if query_result.status_code == 200 and query_result.success:

        capacity_consumed = work_and_speed_functions.calculate_work(query_result.task, query_result.model_dump(), steps=payload.get("steps"))

        await update_contender_capacities(config, contender, capacity_consumed)

        await db_functions.potentially_store_result_in_db(
            config.psql_db, query_result, query_result.task, synthetic_query=synthetic_query, payload=payload
        )
        logger.debug(f"Adjusted node {contender.node_id} for task {query_result.task}.")

    elif query_result.status_code == 429:
        await update_contender_429_count(config, contender)
    else:
        await update_contender_500_count(config, contender)
    return query_result
