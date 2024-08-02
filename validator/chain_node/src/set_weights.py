"""
Get's weights to set from redis, asks signing service to sign, and then sets on chain
"""
import asyncio
import json
import os
from dataclasses import dataclass

import bittensor as bt
import numpy as np
from redis.asyncio import Redis
from redis import Redis as SyncRedis

from validator.utils import redis_constants as rcst, generic_utils as gutils
from validator.chain_node.src.keypair import RedisGappedKeypair
from validator.utils import redis_dataclasses as rdc
from bittensor.utils import weight_utils
from core.logging import get_logger

logger = get_logger(__name__)

MAX_ATTEMPTS = 10
TIME_TO_SLEEP_BETWEEN_ATTEMPTS = 10


@dataclass
class Config:
    redis_host: str
    subtensor_network: str
    netuid: int
    test_env: bool
    redis_db: Redis
    synchronous_redis: SyncRedis
    subtensor: bt.subtensor
    metagraph: bt.metagraph
    wallet: bt.wallet


async def _setup_wallet(redis_db: Redis, synchronous_redis: SyncRedis) -> bt.wallet:
    public_keypair_info = await gutils.get_public_keypair_info(redis_db)
    keypair = RedisGappedKeypair(
        redis_db=synchronous_redis,
        ss58_address=public_keypair_info.ss58_address,
        ss58_format=public_keypair_info.ss58_format,
        crypto_type=public_keypair_info.crypto_type,
        public_key=public_keypair_info.public_key,
    )
    # Doesn't matter what wallet we use here, keypair has the relevant info above
    wallet = bt.wallet()
    wallet._hotkey = keypair
    return wallet


async def load_config() -> Config:
    redis_host = os.getenv("REDIS_HOST", "redis")
    subtensor_network = os.getenv("SUBTENSOR_NETWORK", "finney")
    netuid = int(os.getenv("NETUID", "176"))
    test_env = os.getenv("ENV", "prod").lower() == "test"

    redis_db = Redis(host=redis_host)
    synchronous_redis = SyncRedis(host=redis_host)

    wallet = await _setup_wallet(redis_db, synchronous_redis)
    subtensor = bt.subtensor(network=subtensor_network)
    metagraph = subtensor.metagraph(netuid=netuid)

    return Config(
        redis_host=redis_host,
        subtensor_network=subtensor_network,
        netuid=netuid,
        test_env=test_env,
        redis_db=redis_db,
        synchronous_redis=synchronous_redis,
        subtensor=subtensor,
        metagraph=metagraph,
        wallet=wallet,
    )


async def set_weights(weights_to_set: rdc.WeightsToSet, config: Config) -> None:
    for attempt in range(MAX_ATTEMPTS):
        weights_array = np.zeros_like(config.metagraph.uids, dtype=np.float32)
        for uid, weight in zip(weights_to_set.uids, weights_to_set.values):
            weights_array[uid] = weight

        logger.info(f"weights_array: {weights_array}, metagraph uids: {config.metagraph.uids}")
        processed_weight_uids, processed_weights = weight_utils.process_weights_for_netuid(
            uids=config.metagraph.uids,
            weights=weights_array,
            netuid=weights_to_set.netuid,
            subtensor=config.subtensor,
            metagraph=config.metagraph,
        )

        logger.info(f"Setting weights: {processed_weights} for uids: {processed_weight_uids}....")

        success, message = config.subtensor.set_weights(
            wallet=config.wallet,
            uids=processed_weight_uids,
            weights=processed_weights,
            version_key=weights_to_set.version_key,
            netuid=weights_to_set.netuid,
            wait_for_finalization=True,
            wait_for_inclusion=True,
        )

        if success:
            logger.info("Weights set successfully.")
            return

        logger.error(f"Set weights failed. Attempt {attempt + 1}/{MAX_ATTEMPTS}. Message: {message}")
        await asyncio.sleep(attempt * TIME_TO_SLEEP_BETWEEN_ATTEMPTS)

    logger.error("Failed to set weights after maximum attempts.")


async def poll_for_weights_then_set(config: Config) -> None:
    while True:
        logger.info("Polling redis for weights to set...")
        _, payload_raw = await config.redis_db.blpop(rcst.WEIGHTS_TO_SET_QUEUE_KEY)

        weights_to_set = rdc.WeightsToSet(**json.loads(payload_raw))
        logger.info(f"Setting weights, on netuid: {weights_to_set.netuid}")

        await set_weights(weights_to_set, config)

# TODO: Move this out to testing file
async def main():
    config = await load_config()

    if config.test_env:
        test_weights = rdc.WeightsToSet(
            uids=[0, 1, 2], values=[0.3, 0.01, 0.5], version_key=10000000000, netuid=config.netuid
        )
        await config.redis_db.rpush(rcst.WEIGHTS_TO_SET_QUEUE_KEY, json.dumps(test_weights.__dict__))

    try:
        await poll_for_weights_then_set(config)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        await config.redis_db.close()
        config.synchronous_redis.close()


if __name__ == "__main__":
    asyncio.run(main())
