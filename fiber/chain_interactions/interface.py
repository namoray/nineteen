from substrateinterface import SubstrateInterface
from fiber.chain_interactions import type_registries
from fiber.logging_utils import get_logger
from fiber import constants as fcst


logger = get_logger(__name__)


def _get_chain_endpoint(chain_network: str | None, chain_endpoint: str | None) -> str:
    if chain_network is None and chain_endpoint is None:
        raise ValueError("chain_network and chain_endpoint cannot both be None")

    if chain_endpoint is not None:
        logger.info(f"Using chain endpoint: {chain_endpoint}")
        return chain_endpoint

    if chain_network not in fcst.CHAIN_NETWORK_TO_CHAIN_ADDRESS:
        raise ValueError(f"Unrecognized chain network: {chain_network}")

    chain_endpoint = fcst.CHAIN_NETWORK_TO_CHAIN_ADDRESS[chain_network]
    logger.info(f"Using the chain network: {chain_network} and therefore chain endpoint: {chain_endpoint}")
    return chain_endpoint


def get_substrate_interface(
    chain_network: str | None = fcst.FINNEY_NETWORK, chain_endpoint: str | None = None
) -> SubstrateInterface:
    chain_endpoint = _get_chain_endpoint(chain_network, chain_endpoint)

    type_registry = type_registries.get_type_registry()
    substrate_interface = SubstrateInterface(
        ss58_format=42, use_remote_preset=True, url=chain_endpoint, type_registry=type_registry
    )
    logger.info(f"Connected to {chain_endpoint}")

    return substrate_interface
