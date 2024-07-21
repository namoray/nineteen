import asyncio
from dataclasses import asdict
import json
import os
import time
from redis.asyncio import Redis
from redis import Redis as SyncRedis
import numpy as np
from validator.utils import redis_constants as rcst
from validator.chain_node.keypair import RedisGappedKeypair
from core.logging import get_logger
import bittensor as bt
from validator.utils import redis_dataclasses as rdc
from bittensor.utils import weight_utils

logger = get_logger(__name__)


async def get_public_keypair_info(redis_db: Redis) -> rdc.PublicKeypairInfo:
    logger.info("Getting public key config from Redis...")
    info = await redis_db.get(rcst.PUBLIC_KEYPAIR_INFO_KEY)
    if info is None:
        raise RuntimeError("Could not get public key config from Redis")
    logger.info("Got public key config from Redis!")
    return rdc.PublicKeypairInfo(**json.loads(info))


MAX_ATTEMPTS = 10
TIME_TO_SLEEP_BETWEEN_ATTEMPTS = 10


def _repeatedly_try_to_seight_weights(
    weights_to_set: rdc.WeightsToSet, wallet: bt.wallet, metagraph: bt.metagraph, subtensor: bt.subtensor
) -> None:
    success = False
    attempts = 0

    logger.info(
        f"Will try to set weights for a maximum of {MAX_ATTEMPTS} times and {TIME_TO_SLEEP_BETWEEN_ATTEMPTS * (MAX_ATTEMPTS) * (MAX_ATTEMPTS -1 ) / 2} seconds"
    )
    while not success and attempts < 10:
        weights_array = np.zeros_like(metagraph.uids, dtype=np.float32)
        for uid, weight in zip(weights_to_set.uids, weights_to_set.values):
            weights_array[uid] = weight

        logger.info(f"weights_array: {weights_array}, metagraph uids: {metagraph.uids}")
        (
            processed_weight_uids,
            processed_weights,
        ) = weight_utils.process_weights_for_netuid(
            uids=metagraph.uids,
            weights=weights_array,
            netuid=weights_to_set.netuid,
            subtensor=subtensor,
            metagraph=metagraph,
        )

        logger.info(f"Setting weights: {processed_weights} for uids: {processed_weight_uids}....")

        success, message = subtensor.set_weights(
            wallet=wallet,
            uids=processed_weight_uids,
            weights=processed_weights,
            version_key=weights_to_set.version_key,
            netuid=weights_to_set.netuid,
            wait_for_finalization=True,
            wait_for_inclusion=True,
        )

        if not success:
            attempts += 1
            logger.error(f"Set weights success: {success}.\t Message: {message}")
            logger.info(f"Retrying in {attempts * 10} seconds...")
            time.sleep(attempts * 10)


async def poll_for_weights_then_set(
    redis_db: Redis, wallet: bt.wallet, metagraph: bt.metagraph, subtensor: bt.subtensor
) -> None:
    while True:
        logger.info("Polling redis for weights to set...")
        _, payload_raw = await redis_db.blpop(rcst.WEIGHTS_TO_SET_QUEUE_KEY)

        weights_to_set = rdc.WeightsToSet(**json.loads(payload_raw))

        logger.info(f"Setting weights, on netuid: {weights_to_set.netuid}")

        _repeatedly_try_to_seight_weights(weights_to_set, wallet, metagraph, subtensor)


async def main():
    redis_db = Redis(host="redis")
    sync_redis = SyncRedis(host="redis")
    public_keypair_info = await get_public_keypair_info(redis_db)
    keypair = RedisGappedKeypair(
        redis_db=sync_redis,
        ss58_address=public_keypair_info.ss58_address,
        ss58_format=public_keypair_info.ss58_format,
        crypto_type=public_keypair_info.crypto_type,
        public_key=public_keypair_info.public_key,
    )
    wallet = bt.wallet()
    wallet._hotkey = keypair

    subtensor = bt.subtensor(network=os.getenv("SUBTENSOR_NETWORK", "finney"))
    metagraph = subtensor.metagraph(netuid=os.getenv("NETUID", 176))

    # TODO: Change back to 19
    netuid = os.getenv("NETUID", 176)

    test_env = os.getenv("ENV", "prod").lower() == "test"

    if test_env:
        payload = json.dumps(
            asdict(rdc.WeightsToSet(uids=[0, 1, 2], values=[0.3, 0.01, 0.5], version_key=10000000000, netuid=netuid))
        )
        await redis_db.rpush(
            rcst.WEIGHTS_TO_SET_QUEUE_KEY,
            payload,
        )

    await poll_for_weights_then_set(redis_db, wallet, metagraph, subtensor)


if __name__ == "__main__":
    asyncio.run(main())
