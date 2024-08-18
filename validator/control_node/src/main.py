# TODO: rename core_node (they shoud all be nodes)

import asyncio


# do the rest
import os

from redis.asyncio import Redis

from core import constants as ccst
from core.logging import get_logger

from validator.control_node.src.control_config import Config
from fiber.chain_interactions import interface
from fiber.chain_interactions import chain_utils
from validator.control_node.src.cycle import execute_cycle
from validator.control_node.src.synthetics import refresh_synthetic_data
from validator.db.src.database import PSQLDB
from dotenv import load_dotenv


logger = get_logger(__name__)
load_dotenv()


def load_config() -> Config:
    subtensor_network = os.getenv("SUBTENSOR_NETWORK", "finney")
    subtensor_address = os.getenv("SUBTENSOR_ADDRESS")
    wallet_name = os.getenv("WALLET_NAME", "default")
    hotkey_name = os.getenv("HOTKEY_NAME", "default")
    netuid = os.getenv("NETUID")
    if netuid is None:
        raise ValueError("NETUID must be set")
    else:
        netuid = int(netuid)

    substrate_interface = interface.get_substrate_interface(
        subtensor_network=subtensor_network, subtensor_address=subtensor_address
    )
    keypair = chain_utils.load_hotkey_keypair(wallet_name=wallet_name, hotkey_name=hotkey_name)

    return Config(
        substrate_interface=substrate_interface,
        keypair=keypair,
        psql_db=PSQLDB(),
        redis_db=Redis(host="redis"),
        test_env=os.getenv("ENV", "test") == "test",
        subtensor_network=subtensor_network,
        subtensor_address=subtensor_address,
        netuid=netuid,
        seconds_between_syncs=int(os.getenv("SECONDS_BETWEEN_SYNCS", str(ccst.SCORING_PERIOD_TIME))),
        replace_with_docker_localhost=True,
    )


async def main() -> None:
    config = load_config()
    await config.psql_db.connect()

    await asyncio.gather(
        # score_results.main(),  # Should be in its own thread
        refresh_synthetic_data.main(),  # Should be in its own thread
        execute_cycle.single_cycle(config),
    )


if __name__ == "__main__":
    asyncio.run(main())
