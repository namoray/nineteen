import asyncio
import json
from substrateinterface import Keypair
from redis.asyncio import Redis
import os
from validator.signing_service import utils, constants as cst

logger = utils.get_logger(__name__)


def sign_message(message: str, keypair: Keypair):
    return f"0x{keypair.sign(message).hex()}"


async def sign_and_push(redis_db: Redis, message: str, job_id: str, keypair: Keypair):
    signed_message = sign_message(message, keypair=keypair)
    logger.debug(f"Signed message: {signed_message}")
    await redis_db.set(
        utils.construct_signed_message_key(job_id),
        json.dumps({cst.SIGNED_MESSAGE: signed_message, cst.JOB_ID: job_id}),
        ex=5,
    )


async def poll_redis_for_message_to_sign(redis_db: Redis, keypair: Keypair) -> str:
    logger.info("Polling redis for message to sign")

    while True:
        payload_raw: tuple[str, bytes] = await redis_db.blpop(cst.SIGNING_QUEUE_KEY)

        payload = json.loads(payload_raw[1].decode("utf-8"))
        logger.debug(payload)
        await sign_and_push(redis_db, payload[cst.MESSAGE], payload[cst.JOB_ID], keypair)


async def main() -> None:
    wallet_name = os.getenv("WALLET_NAME", "default")
    hotkey_name = os.getenv("HOTKEY_NAME", "default")

    redis_db = Redis(host="redis")

    await redis_db.rpush(
        cst.SIGNING_QUEUE_KEY,
        json.dumps({cst.TYPE: cst.DENDRITE_TYPE, cst.MESSAGE: "Starting signing service", "job_id": 0}),
    )

    filepath = utils.construct_wallet_path(wallet_name, hotkey_name)
    keypair = utils.load_keypair_from_file(filepath)
    await poll_redis_for_message_to_sign(redis_db, keypair)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting...")
