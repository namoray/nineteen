"""
TODO: Make this more secure so it will only sign certain things
"""

import asyncio
import json
from substrateinterface import Keypair
from redis.asyncio import Redis
import os
from validator.signing_service.src import utils, constants as cst
from dataclasses import asdict
from validator.signing_service.src import signing_dataclasses as dc

logger = utils.get_logger(__name__)


def sign_message(message: str, keypair: Keypair) -> str:
    return f"0x{keypair.sign(message).hex()}"


async def sign_and_push(redis_db: Redis, message: str, job_id: str, keypair: Keypair):
    signed_message = sign_message(message, keypair=keypair)
    signed_payload = dc.SignedPayload(signature=signed_message, job_id=job_id)
    logger.debug("Signed message!")
    await redis_db.lpush(
        utils.construct_signed_message_key(job_id),
        json.dumps(asdict(signed_payload)),
    )
    await redis_db.expire(utils.construct_signed_message_key(job_id), 5)


async def poll_redis_for_message_to_sign(redis_db: Redis, keypair: Keypair, run_once: bool = False) -> str:
    logger.info("Polling redis for message to sign")
    while True:
        _, payload_raw = await redis_db.blpop(keys=[cst.SIGNING_DENDRITE_QUEUE_KEY, cst.SIGNING_WEIGHTS_QUEUE_KEY])
        payload = dc.SigningPayload.from_dict(json.loads(payload_raw))
        await sign_and_push(redis_db, payload.message, payload.job_id, keypair)

        if run_once:
            break

# Dont bother, just cahnge this to respond to a request for public info in the same way
async def post_and_refresh_public_key_info(redis_db: Redis, keypair: Keypair, run_once: bool = False):
    ss58_address = keypair.ss58_address
    public_key_format = keypair.ss58_format
    crypto_type = keypair.crypto_type
    public_key = keypair.public_key.hex()

    public_key_info = dc.PublicKeypairInfo(
        ss58_address=ss58_address,
        ss58_format=public_key_format,
        crypto_type=crypto_type,
        public_key=public_key,
    )
    while True:
        logger.info("Pushing public key info to redis...")
        await redis_db.set(cst.PUBLIC_KEYPAIR_INFO_KEY, json.dumps(asdict(public_key_info)))

        if run_once:
            break
        logger.info("Sleeping for 60, then will refresh public key info again")
        await asyncio.sleep(60)


async def main() -> None:
    wallet_name = os.getenv("WALLET_NAME", "default")
    hotkey_name = os.getenv("HOTKEY_NAME", "default")

    filepath = utils.construct_wallet_path(wallet_name, hotkey_name)
    keypair = utils.load_keypair_from_file(filepath)


    redis_db = Redis(host="redis")
    run_once = os.getenv("RUN_ONCE", "false").lower() == "true"

    starting_signing_service_data = dc.SigningPayload(
        message="Starting signing service",
        job_id=0,
        is_b64encoded=False,
    )
    await redis_db.rpush(
        cst.SIGNING_DENDRITE_QUEUE_KEY,
        json.dumps(starting_signing_service_data.to_dict()),
    )


    tasks = [
        post_and_refresh_public_key_info(redis_db, keypair, run_once),
        poll_redis_for_message_to_sign(redis_db, keypair, run_once),
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
    finally:
        logger.info("Signing service stopped.")
