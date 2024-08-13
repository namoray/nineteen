# TODO: rename core_node (they shoud all be nodes)

import asyncio

from pydantic import Field
from validator.control_node.src.weights import calculate_and_schedule_weights as calculate_weights

# do the rest
from validator.control_node.src.score_results import score_results
import os
from core import constants as ccst
from pydantic_settings import BaseSettings
from core.logging import get_logger

from validator.control_node.src.cycle import refresh_contenders, refresh_nodes
from substrateinterface import SubstrateInterface, Keypair

from fiber.chain_interactions import interface
from fiber.chain_interactions import chain_utils

from validator.db.src.database import PSQLDB

logger = get_logger(__name__)


class Config(BaseSettings):
    psql_db: PSQLDB = Field(default_factory=PSQLDB)
    test_env: bool = Field(env="ENV", default="test")
    network: str = Field(env="SUBTENSOR_NETWORK")
    netuid: int = Field(env="NETUID", default=19)
    seconds_between_syncs: int = Field(env="SECONDS_BETWEEN_SYNCS", default=ccst.SCORING_PERIOD_TIME)
    substrate_interface: SubstrateInterface
    keypair: Keypair

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# TODO: better co-ordinate these instead of jsut startin them all off
async def main() -> None:
    subtensor_address = os.getenv("SUBTENSOR_ADDRESS")
    wallet_name = os.getenv("WALLET_NAME", "default")
    hotkey_name = os.getenv("HOTKEY_NAME", "default")
    subtensor_network = os.getenv("SUBTENSOR_NETWORK", "finney")

    substrate_interface = interface.get_substrate_interface(
        subtensor_network=subtensor_network, subtensor_address=subtensor_address
    )
    keypair = chain_utils.load_hotkey_keypair(wallet_name=wallet_name, hotkey_name=hotkey_name)

    await asyncio.gather(
        score_results.main(),  # Should be in its own thread
        refresh_synthetic_data.main(),  # Should be in its own thread
        calculate_weights.main(),  # pbut with a cycle
        refresh_contenders.main(),  # put with a cycle
        schedule_synthetic_queries.main(),  # Put with a cycle
        refresh_nodes.main(substrate_interface=substrate_interface, keypair=keypair),  # put with cycle
    )


if __name__ == "__main__":
    asyncio.run(main())
