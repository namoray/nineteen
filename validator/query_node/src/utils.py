from core.models import utility_models
from validator.models import Contender
from validator.query_node.src.query_config import Config
from validator.utils import work_and_speed_functions
from core.logging import get_logger
from validator.db.src import functions as db_functions
from validator.db.src.sql.contenders import update_contender_429_count, update_contender_500_count, update_contender_capacities

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
        # TODO: FIX the steps bit
        capacity_consumed = work_and_speed_functions.calculate_work(query_result.task, query_result, steps=None)

        await update_contender_capacities(config, contender, capacity_consumed)

        await db_functions.potentially_store_result_in_db(
            config.psql_db, query_result, query_result.task, synthetic_query=synthetic_query, payload=payload
        )
        logger.debug(f"Adjusted contender: {contender.id} for task: {query_result.task}")

    elif query_result.status_code == 429:
        await update_contender_429_count(config, contender)
    else:
        await update_contender_500_count(config, contender)
    return query_result


# def get_formatted_response(
#     resulting_synapse: base_models.BaseSynapse, initial_synapse: bt.Synapse
# ) -> Optional[BaseModel]:
#     if resulting_synapse and resulting_synapse.dendrite.status_code == 200 and resulting_synapse != initial_synapse:
#         formatted_response = _extract_response(resulting_synapse, initial_synapse)
#         return formatted_response
#     else:
#         return None

# async def query_miner_no_stream(
#     contender: Contender,
#     outgoing_model: BaseModel,
#     task: Task,
#     synthetic_query: bool,
# ) -> utility_models.QueryResult:
#     axon_uid = contender.node_hotkey
#     axon = contender.axon
#     resulting_synapse, response_time = await qutils.query_individual_axon(
#         synapse=synapse, dendrite=dendrite, axon=axon, uid=axon_uid, log_requests_and_responses=False
#     )

#     # IDE doesn't recognise the above typehints, idk why? :-(
#     resulting_synapse: base_models.BaseSynapse
#     response_time: float

#     formatted_response = get_formatted_response(resulting_synapse, outgoing_model)
#     if formatted_response is not None:
#         bt.logging.info(f"✅ Successfully queried axon: {axon_uid} for task: {task}")
#         query_result = utility_models.QueryResult(
#             formatted_response=formatted_response,
#             axon_uid=axon_uid,
#             response_time=response_time,
#             task=task,
#             success=True,
#             node_hotkey=contender.node_hotkey,
#             status_code=resulting_synapse.axon.status_code,
#             error_message=resulting_synapse.error_message,
#         )
#         # create_scoring_adjustment_task(query_result, synapse, contender, synthetic_query)
#         return query_result

#     elif task == Task.avatar:
#         query_result = utility_models.QueryResult(
#             formatted_response=formatted_response,
#             axon_uid=axon_uid,
#             response_time=response_time,
#             task=task,
#             success=False,
#             node_hotkey=contender.node_hotkey,
#             status_code=resulting_synapse.axon.status_code,
#             error_message=resulting_synapse.error_message,
#         )
#         # create_scoring_adjustment_task(query_result, synapse, contender, synthetic_query)

#     else:
#         query_result = utility_models.QueryResult(
#             formatted_response=None,
#             axon_uid=axon_uid,
#             response_time=None,
#             error_message=resulting_synapse.axon.status_message,
#             task=task,
#             status_code=resulting_synapse.axon.status_code,
#             success=False,
#             node_hotkey=contender.node_hotkey,
#         )
#         # create_scoring_adjustment_task(query_result, synapse, contender, synthetic_query)
#         return query_result


# def _extract_response(resulting_synapse: base_models.BaseSynapse, outgoing_model: BaseModel) -> Optional[BaseModel]:
#     try:
#         formatted_response = outgoing_model(**resulting_synapse.dict())

#         # If we're expecting a result (i.e. not nsfw), then try to deserialize
#         if (hasattr(formatted_response, "is_nsfw") and not formatted_response.is_nsfw) or not hasattr(
#             formatted_response, "is_nsfw"
#         ):
#             deserialized_result = resulting_synapse.deserialize()
#             if deserialized_result is None:
#                 formatted_response = None

#         return formatted_response
#     except ValidationError as e:
#         bt.logging.debug(f"Failed to deserialize for some reason: {e}")
#         return None


# async def query_individual_axon_stream(
#     dendrite: bt.dendrite,
#     axon: bt.axon,
#     axon_uid: int,
#     synapse: bt.Synapse,
#     deserialize: bool = False,
#     log_requests_and_responses: bool = True,
# ):
#     synapse_name = synapse.__class__.__name__
#     if synapse_name not in cst.OPERATION_TIMEOUTS:
#         bt.logging.warning(f"Operation {synapse_name} not in operation_to_timeout, this is probably a mistake / bug 🐞")
#     if log_requests_and_responses:
#         bt.logging.info(f"Querying axon {axon_uid} for {synapse_name}")
#     response = await dendrite.forward(
#         axons=axon,
#         synapse=synapse,
#         connect_timeout=0.3,
#         response_timeout=5,  # if X seconds without any data, its boinked
#         deserialize=deserialize,
#         log_requests_and_responses=log_requests_and_responses,
#         streaming=True,
#     )
#     return response
