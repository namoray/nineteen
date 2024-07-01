import asyncio
import threading
from typing import Any, List

import bittensor as bt
from config import configuration
from models import utility_models

from redis.asyncio import Redis
from vali_new.core.utils import redis_utils
from vali_new.core import constants as cst

from collections import defaultdict
from typing import Dict, Tuple
from typing import Optional

from core import Task
from validation.proxy.utils import query_utils
from core import bittensor_overrides as bto
from models import base_models, synapses


# Replace with some global threading lock?
threading_lock = threading.Lock()


async def fetch_miner_info(redis_db: Redis, metagraph: bt.metagraph, subtensor: bt.subtensor):
    hotkeys = await _fetch_data_from_metagraph(redis_db, metagraph, subtensor)
    capacities_for_tasks = await _fetch_available_capacities_for_each_axon(hotkeys)
    corrected_capacities = _correct_capacities(capacities_for_tasks)
    await _store_capacities_in_redis(corrected_capacities)


async def _fetch_data_from_metagraph(redis_db: Redis, metagraph: bt.metagraph, subtensor: bt.subtensor) -> None:
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
            # TODO: Is this the best way to store the info?
            await redis_utils.save_json_to_redis(redis_db, cst.HOTKEY_INFO_KEY + hotkey, hotkey_info.dict())

    return hotkeys


async def _fetch_available_capacities_for_each_axon(
    redis_db: Redis, hotkeys: List[str], dendrite: bto.dendrite
) -> None:
    hotkey_to_query_task = {}

    for hotkey in hotkeys:
        # NOTE: Doesn't seem the most efficient to use redis here... lol
        hotkey_info = utility_models.HotkeyInfo(
            **(await redis_utils.load_json_from_redis(redis_db, cst.HOTKEY_INFO_KEY + hotkey))
        )
        task = asyncio.create_task(
            query_utils.query_individual_axon(
                synapse=synapses.Capacity(),
                dendrite=dendrite,
                axon=hotkey_info.axon,
                uid=hotkey_info.uid,
                deserialize=True,
                log_requests_and_responses=False,
            )
        )

        hotkey_to_query_task[hotkey] = task

    responses_and_response_times: List[
        Tuple[Optional[Dict[Task, base_models.VolumeForTask]], float]
    ] = await asyncio.gather(*hotkey_to_query_task.values())

    all_capacities = [i[0] for i in responses_and_response_times]

    bt.logging.info(f"Got capacities from {len([i for i in all_capacities if i is not None])} axons!")
    with threading_lock:
        capacities_for_tasks = defaultdict(lambda: {})
        for hotkey, capacities in zip(hotkeys, all_capacities):
            if capacities is None:
                continue

            allowed_tasks = set([task for task in Task])
            for task, volume in capacities.items():
                # This is to stop people claiming tasks that don't exist
                if task not in allowed_tasks:
                    continue
                if hotkey not in capacities_for_tasks[task]:
                    capacities_for_tasks[task][hotkey] = float(volume.volume)
        return capacities_for_tasks


def _correct_capacities(capacities_for_tasks: Dict[Any, Dict[str, float]]):
    return capacities_for_tasks


async def _store_capacities_in_redis(redis_db: Redis, capacities_for_tasks: Dict[Any, Dict[str, float]]):
    await redis_utils.save_json_to_redis(redis_db, cst.CAPACITIES_KEY, capacities_for_tasks)


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
