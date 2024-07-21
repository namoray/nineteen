import asyncio
from dataclasses import asdict
import json
import os
from redis.asyncio import Redis

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
    return rdc.PublicKeypairInfo(**json.loads(info))


def poll_for_weights_then_set(
    redis_db: Redis, wallet: bt.wallet, subtensor: bt.subtensor, without_set: bool = False
) -> None:
    while True:
        _, payload_raw = redis_db.blpop(rcst.SIGNING_WEIGHTS_QUEUE_KEY, timeout=10)
        payload = rdc.WeightsToSet(**json.loads(payload_raw.decode("utf-8")))
        logger.debug(f"Got payload: {payload}")


async def main():
    redis_db = Redis(host="redis")
    public_keypair_info = await get_public_keypair_info(redis_db)
    keypair = RedisGappedKeypair(
        redis_db=redis_db,
        ss58_address=public_keypair_info.ss58_address,
        ss58_format=public_keypair_info.ss58_format,
        crypto_type=public_keypair_info.crypto_type,
        public_key=public_keypair_info.public_key,
    )
    wallet = bt.wallet()
    wallet.hotkey = keypair

    subtensor = bt.subtensor(network=os.getenv("NETWORK", "finney"))

    test_env = os.getenv("ENV", "prod").lower() == "test"

    if test_env:
        await redis_db.rpush(
            rcst.SIGNING_WEIGHTS_QUEUE_KEY, asdict(rdc.WeightsToSet(uids=[0, 1, 2], values=[1, 1, 0], version_key=100))
        )

    await poll_for_weights_then_set(redis_db, wallet, subtensor, without_set=test_env)


if __name__ == "__main__":
    asyncio.run(main())