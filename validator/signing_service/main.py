import asyncio
import json
from substrateinterface import Keypair
from redis.asyncio import Redis
import os
from validator.signing_service import utils, constants as cst
from dataclasses import asdict

logger = utils.get_logger(__name__)


async def post_and_refresh_public_key_info(redis_db: Redis, keypair: Keypair):
    public_key = keypair.ss58_address
    public_key_format = keypair.ss58_format
    crypto_type = keypair.crypto_type
    public_key = keypair.public_key.hex()

    public_key_info = utils.PublicKeypairInfo(
        ss58_address=public_key,
        ss58_format=public_key_format,
        crypto_type=crypto_type,
        public_key=public_key,
    )
    while True:
        logger.info("Pushing public key info to redis...")
        await redis_db.set(cst.PUBLIC_KEYPAIR_INFO_KEY, json.dumps(asdict(public_key_info)))
        logger.info("Sleeping for 60, then will refresh public key info again")
        await asyncio.sleep(60)


def sign_message(message: str, keypair: Keypair):
    return f"0x{keypair.sign(message).hex()}"


async def sign_and_push(redis_db: Redis, message: str, job_id: str, keypair: Keypair):
    signed_message = sign_message(message, keypair=keypair)
    logger.debug(f"Signed message: {signed_message}")
    await redis_db.lpush(
        utils.construct_signed_message_key(job_id),
        json.dumps({cst.SIGNATURE: signed_message, cst.JOB_ID: job_id}),
    )
    await redis_db.expire(utils.construct_signed_message_key(job_id), 5)


async def poll_redis_for_message_to_sign(redis_db: Redis, keypair: Keypair, run_once: bool = False) -> str:
    logger.info("Polling redis for message to sign")

    while True:
        payload_raw: tuple[str, bytes] = await redis_db.blpop(
            keys=[cst.SIGNING_DENDRITE_QUEUE_KEY, cst.SIGNING_WEIGHTS_QUEUE_KEY]
        )

        payload = json.loads(payload_raw[1].decode("utf-8"))
        logger.debug(payload)
        await sign_and_push(redis_db, payload[cst.MESSAGE], payload[cst.JOB_ID], keypair)

        if run_once:
            break


async def main() -> None:
    wallet_name = os.getenv("WALLET_NAME", "default")
    hotkey_name = os.getenv("HOTKEY_NAME", "default")

    redis_db = Redis(host="redis")
    run_once = os.getenv("RUN_ONCE", "false").lower() == "true"

    await redis_db.rpush(
        cst.SIGNING_DENDRITE_QUEUE_KEY,
        json.dumps({cst.MESSAGE: "Starting signing service", "job_id": 0}),
    )

    filepath = utils.construct_wallet_path(wallet_name, hotkey_name)
    keypair = utils.load_keypair_from_file(filepath)

    tasks = [
        post_and_refresh_public_key_info(redis_db, keypair),
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
