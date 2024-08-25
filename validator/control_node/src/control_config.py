# TODO: rename core_node (they shoud all be nodes)

from dataclasses import dataclass


# do the rest
import os

import httpx
from core.logging import get_logger

from substrateinterface import SubstrateInterface, Keypair

from validator.db.src.database import PSQLDB
from dotenv import load_dotenv
from redis.asyncio import Redis

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
    netuid: int
    seconds_between_syncs: int
    replace_with_localhost: bool
    replace_with_docker_localhost: bool 
    refresh_nodes: bool
    capacity_to_score_multiplier: float
    httpx_client: httpx.AsyncClient = httpx.AsyncClient()
    debug: bool = os.getenv("ENV", "prod").lower() == "dev"
