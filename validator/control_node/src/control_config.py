from dataclasses import dataclass
import os
from redis.asyncio import Redis

from core import constants as ccst
from core.logging import get_logger

from fiber.chain_interactions import interface
from fiber.chain_interactions import chain_utils


from validator.db.src.database import PSQLDB

import httpx

from substrateinterface import SubstrateInterface, Keypair

from dotenv import load_dotenv

logger = get_logger(__name__)
load_dotenv()


@dataclass
class Config:
    substrate_interface: SubstrateInterface
    keypair: Keypair
    psql_db: PSQLDB
    redis_db: Redis
    test_env: bool
    subtensor_network: str
    subtensor_address: str
    gpu_server_address: str
    netuid: int
    seconds_between_syncs: int
    replace_with_localhost: bool
    replace_with_docker_localhost: bool
    refresh_nodes: bool
    capacity_to_score_multiplier: float
    httpx_client: httpx.AsyncClient = httpx.AsyncClient()
    debug: bool = os.getenv("ENV", "prod").lower() == "dev"


def load_config() -> Config:
    subtensor_network = os.getenv("SUBTENSOR_NETWORK", "finney")
    subtensor_address = os.getenv("SUBTENSOR_ADDRESS")
    gpu_server_address: str | None = os.getenv("GPU_SERVER_ADDRESS")
    if gpu_server_address is None:
        raise ValueError("GPU_SERVER_ADDRESS must be set")

    wallet_name = os.getenv("WALLET_NAME", "default")
    hotkey_name = os.getenv("HOTKEY_NAME", "default")
    netuid = os.getenv("NETUID")
    if netuid is None:
        raise ValueError("NETUID must be set")
    else:
        netuid = int(netuid)

    localhost = bool(os.getenv("LOCALHOST", "false").lower() == "true")
    if localhost:
        redis_host = "localhost"
        os.environ["POSTGRES_HOST"] = "localhost"
    else:
        redis_host = os.getenv("REDIS_HOST", "redis")

    replace_with_docker_localhost = bool(os.getenv("REPLACE_WITH_DOCKER_LOCALHOST", "false").lower() == "true")

    refresh_nodes: bool = os.getenv("REFRESH_NODES", "true").lower() == "true"
    if refresh_nodes:
        substrate_interface = interface.get_substrate_interface(
            subtensor_network=subtensor_network, subtensor_address=subtensor_address
        )
    else:
        substrate_interface = None
    keypair = chain_utils.load_hotkey_keypair(wallet_name=wallet_name, hotkey_name=hotkey_name)

    default_capacity_to_score_multiplier = 0.1 if subtensor_network == "test" else 1.0
    logger.info(f"Capacity to score multiplier: {default_capacity_to_score_multiplier}")
    capacity_to_score_multiplier = float(os.getenv("CAPACITY_TO_SCORE_MULTIPLIER", default_capacity_to_score_multiplier))

    return Config(
        substrate_interface=substrate_interface,
        keypair=keypair,
        psql_db=PSQLDB(),
        redis_db=Redis(host=redis_host),
        test_env=os.getenv("ENV", "test") == "test",
        subtensor_network=subtensor_network,
        subtensor_address=subtensor_address,
        netuid=netuid,
        seconds_between_syncs=int(os.getenv("SECONDS_BETWEEN_SYNCS", str(ccst.SCORING_PERIOD_TIME))),
        replace_with_docker_localhost=replace_with_docker_localhost,
        replace_with_localhost=localhost,
        refresh_nodes=refresh_nodes,
        capacity_to_score_multiplier=capacity_to_score_multiplier,
        gpu_server_address=gpu_server_address,
    )
