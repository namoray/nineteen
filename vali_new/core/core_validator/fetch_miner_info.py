import asyncio
import threading
from typing import List

import bittensor as bt
from config import configuration
from models import utility_models

from redis.asyncio import Redis
from vali_new.core.utils import redis_utils
from vali_new.core import constants as cst

# Replace with some global threading lock?
threading_lock = threading.Lock()


async def fetch_miner_info(redis_db: Redis, metagraph: bt.metagraph, subtensor: bt.subtensor):
    await _fetch_data_from_metagraph(redis_db, metagraph, subtensor)
    await _fetch_available_capacities_for_each_axon()


async def _fetch_data_from_metagraph(redis_db: Redis, metagraph: bt.metagraph, subtensor: bt.subtensor):
    bt.logging.info("Resyncing the metagraph!")
    await asyncio.to_thread(metagraph.sync, subtensor=subtensor, lite=True)

    bt.logging.info("Got the capacities, now storing the info....")
    _, axon_indexes_tensor = metagraph.incentive.sort(descending=True)

    with threading_lock:
        uids: List[int] = metagraph.uids.tolist()
        axon_indexes = axon_indexes_tensor.tolist()
        hotkeys: List[str] = metagraph.hotkeys  # noqa: F841
        axons = metagraph.axons

        for i in axon_indexes:
            uid, hotkey, axon = uids[i], hotkeys[i], axons[i]
            hotkey_info = utility_models.HotkeyInfo(
                uid=uid,
                axon=axon,
                hotkey=hotkey,
            )
            await redis_utils.save_json_to_redis(redis_db, cst.HOTKEY_INFO_KEY + hotkey, hotkey_info.dict())

    bt.logging.info("Finished extraction - now to fetch the available capacities for each axon")


async def _fetch_available_capacities_for_each_axon(): ...


async def main():
    redis_db = Redis()

    def prepare_config_and_logging() -> bt.config:
        base_config = configuration.get_validator_cli_config()

        bt.logging(config=base_config, logging_dir=base_config.full_path)
        return base_config

    config = prepare_config_and_logging()
    subtensor = bt.subtensor(config=config)
    metagraph = subtensor.metagraph(netuid=config.netuid, lite=True)

    await fetch_miner_info(redis_db, metagraph, subtensor)


if __name__ == "__main__":
    asyncio.run(main())
