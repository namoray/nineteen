import asyncio
from dataclasses import asdict
import json
import os
from redis.asyncio import Redis
from redis import Redis as SyncRedis

from validator.utils import redis_constants as rcst
from validator.chain_node.keypair import RedisGappedKeypair
from core.logging import get_logger
import bittensor as bt
from validator.utils import redis_dataclasses as rdc

logger = get_logger(__name__)


async def get_public_keypair_info(redis_db: Redis) -> rdc.PublicKeypairInfo:
    logger.info("Getting public key config from Redis...")
    info = await redis_db.get(rcst.PUBLIC_KEYPAIR_INFO_KEY)
    if info is None:
        raise RuntimeError("Could not get public key config from Redis")
    logger.info("Got public key config from Redis!")
    return rdc.PublicKeypairInfo(**json.loads(info))


async def poll_for_weights_then_set(redis_db: Redis, wallet: bt.wallet, subtensor: bt.subtensor) -> None:
    while True:
        logger.info("Polling redis for weights to set...")
        _, payload_raw = await redis_db.blpop(rcst.WEIGHTS_TO_SET_QUEUE_KEY)

        payload = rdc.WeightsToSet(**json.loads(payload_raw))

        logger.info(f"Setting weights, on netuid: {payload.netuid}")

        subtensor.set_weights(
            wallet=wallet,
            uids=payload.uids,
            weights=payload.values,
            version_key=payload.version_key,
            netuid=payload.netuid,
            wait_for_finalization=True,
            wait_for_inclusion=True,
        )


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

    # TODO: Change back to 19
    netuid = os.getenv("NETUID", 176)

    test_env = os.getenv("ENV", "prod").lower() == "test"

    if test_env:
        payload = json.dumps(asdict(rdc.WeightsToSet(uids=[0, 1, 2], values=[1, 1, 0], version_key=100, netuid=netuid)))
        await redis_db.rpush(
            rcst.WEIGHTS_TO_SET_QUEUE_KEY,
            payload,
        )

    await poll_for_weights_then_set(redis_db, wallet, subtensor)


if __name__ == "__main__":
    asyncio.run(main())
