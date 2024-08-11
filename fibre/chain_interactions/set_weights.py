from tenacity import retry
from substrateinterface import Keypair, SubstrateInterface
from scalecodec import ScaleType
from fibre import constants as fcst
from fibre.logging_utils import get_logger

from tenacity import stop_after_attempt, wait_exponential
from functools import wraps
from typing import Callable, Any


logger = get_logger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def _query_subtensor(
    substrate: SubstrateInterface, name: str, block: int | None = None, params: int | None = None
) -> ScaleType:
    return substrate.query(
        module="SubtensorModule",
        storage_function=name,
        params=params,
        block_hash=(None if block is None else substrate.get_block_hash(block)),
    )


def _get_hyperparameter(
    substrate_interface: SubstrateInterface, param_name: str, netuid: int, block: int | None = None
) -> list[int] | None:
    subnet_exists = getattr(_query_subtensor(substrate_interface, "NetworksAdded", block, [netuid]), "value", False)
    if not subnet_exists:
        return None
    return getattr(_query_subtensor(substrate_interface, param_name, block, [netuid]), "value", None)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def _get_current_block(substrate_interface: SubstrateInterface) -> int:
    return substrate_interface.get_block_number(None)  # type: ignore


def _blocks_since_last_update(substrate_interface: SubstrateInterface, netuid: int, node_id: int) -> int | None:
    current_block = _get_current_block(substrate_interface)
    last_updated = _get_hyperparameter(substrate_interface, "LastUpdate", netuid)
    return None if last_updated is None else current_block - int(last_updated[node_id])


def _min_interval_to_set_weights(substrate_interface: SubstrateInterface, netuid: int) -> int:
    return _get_hyperparameter(substrate_interface, "WeightsSetRateLimit", netuid)


def _normalize_and_quantize_weights(node_ids: list[int], node_weights: list[float]) -> tuple[list[int], list[int]]:
    if (
        len(node_ids) != len(node_weights)
        or any(uid < 0 for uid in node_ids)
        or any(weight < 0 for weight in node_weights)
    ):
        raise ValueError("Invalid input: length mismatch or negative values")
    if not any(node_weights):
        return [], []
    scaling_factor = fcst.U16_MAX / max(node_weights)

    node_weights_formatted = []
    node_ids_formatted = []
    for node_id, node_weight in zip(node_ids, node_weights):
        if node_weight > 0:
            node_ids_formatted.append(node_id)
            node_weights_formatted.append(int(node_weight * scaling_factor))

    return node_ids_formatted, node_weights_formatted


def _format_error_message(error_message: dict) -> str:
    err_type, err_name, err_description = "UnknownType", "UnknownError", "Unknown Description"
    if isinstance(error_message, dict):
        err_type = error_message.get("type", err_type)
        err_name = error_message.get("name", err_name)
        err_description = error_message.get("docs", [err_description])[0]
    return f"Subtensor returned `{err_name} ({err_type})` error. This means: `{err_description}`"


def log_and_reraise(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Exception in {func.__name__}: {str(e)}")
            raise

    return wrapper


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
@log_and_reraise
def _set_node_weights_on_chain(
    substrate_interface: SubstrateInterface,
    keypair: Keypair,
    node_ids: list[int],
    node_weights: list[int],
    netuid: int,
    version_key: int,
    wait_for_inclusion: bool = False,
    wait_for_finalization: bool = False,
) -> tuple[bool, str | None]:
    call = substrate_interface.compose_call(
        call_module="SubtensorModule",
        call_function="set_weights",
        call_params={"dests": node_ids, "weights": node_weights, "netuid": netuid, "version_key": version_key},
    )

    extrinsic = substrate_interface.create_signed_extrinsic(call=call, keypair=keypair, era={"period": 5})
    response = substrate_interface.submit_extrinsic(
        extrinsic, wait_for_inclusion=wait_for_inclusion, wait_for_finalization=wait_for_finalization
    )
    if not wait_for_finalization and not wait_for_inclusion:
        return True, "Not waiting for finalization or inclusion."
    response.process_events()

    if response.is_success:
        return True, "Successfully set weights."

    return False, _format_error_message(response.error_message)


def set_node_weights(
    substrate_interface: SubstrateInterface,
    keypair: Keypair,
    node_ids: list[int],
    node_weights: list[float],
    netuid: int,
    validator_node_id: int,
    version_key: int = 0,
    wait_for_inclusion: bool = False,
    wait_for_finalization: bool = False,
    max_attempts: int = 1,
) -> tuple[bool, str]:
    attempts = 0
    success = False
    message = "No attempt made. Perhaps it is too soon to set weights!"

    while attempts < max_attempts:
        blocks_since_update = _blocks_since_last_update(substrate_interface, netuid, validator_node_id)
        min_interval = _min_interval_to_set_weights(substrate_interface, netuid)

        if blocks_since_update is None or blocks_since_update <= min_interval:
            logger.info(
                f"Skipping attempt {attempts + 1}/{max_attempts}. Blocks since last update: {blocks_since_update}, Min interval: {min_interval}"
            )
            attempts += 1
            continue

        logger.info(f"Attempting to set weights (Attempt {attempts + 1}/{max_attempts})")
        node_ids_formatted, node_weights_formatted = _normalize_and_quantize_weights(node_ids, node_weights)

        success, error_message = _set_node_weights_on_chain(
            substrate_interface=substrate_interface,
            keypair=keypair,
            netuid=netuid,
            node_ids=node_ids_formatted,
            node_weights=node_weights_formatted,
            version_key=version_key,
            wait_for_finalization=wait_for_finalization,
            wait_for_inclusion=wait_for_inclusion,
        )

        if not wait_for_finalization and not wait_for_inclusion:
            return True, "Not waiting for finalization or inclusion."

        if success:
            logger.info(f"Set weights - Finalized: {success}")
            message = "Successfully set weights and Finalized."
        else:
            logger.error(f"Failed to set weights: {error_message}")
            message = error_message

        return success, message

    logger.warning(f"Max attempts ({max_attempts}) reached without success")
    return success, message
