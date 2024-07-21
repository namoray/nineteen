import asyncio
import json
from substrateinterface import Keypair
from redis.asyncio import Redis
import os
from validator.signing_service import utils, constants as cst

logger = utils.get_logger(__name__)


# Constants here to minimise dependencies





def load_keypair_from_file(file_path: str, password=""):
    try:
        with open(file_path, "r") as file:
            keypair_data = json.load(file)
        keypair = Keypair.create_from_seed(keypair_data["secretSeed"])
        logger.info(f"Loaded keypair from {file_path}")
        return keypair
    except Exception as e:
        raise ValueError(f"Failed to load keypair: {str(e)}")


def sign_message(message: str, keypair: Keypair):
    return f"0x{keypair.sign(message).hex()}"


async def sign_and_push(redis_db: Redis, message: str, job_id: str, keypair: Keypair):
    signed_message = sign_message(message, keypair=keypair)
    logger.debug(f"Signed message: {signed_message}")
    await redis_db.set(
        utils.construct_signed_message_key(job_id), json.dumps({cst.SIGNED_MESSAGE: signed_message, cst.JOB_ID: job_id}), ex=5
    )


async def poll_redis_for_message_to_sign(redis_db: Redis, keypair: Keypair) -> str:
    logger.info("Polling redis for message to sign")

    while True:
        payload_raw = await redis_db.blpop(cst.SIGNING_QUEUE_KEY)

        payload = json.loads(payload_raw[1].decode("utf-8"))
        logger.debug(payload)
        await sign_and_push(redis_db, payload[cst.MESSAGE], payload[cst.JOB_ID], keypair)


async def main() -> None:
    wallet_name = os.getenv("WALLET_NAME")
    hotkey_name = os.getenv("HOTKEY_NAME")
    password = os.getenv("HOTKEY_PASSWORD", "")

    redis_db = Redis(host="redis")

    await redis_db.rpush(
        cst.SIGNING_QUEUE_KEY, json.dumps({cst.TYPE: cst.DENDRITE_TYPE, cst.MESSAGE: "Starting signing service", "job_id": 0})
    )

    filepath = utils.construct_wallet_path(wallet_name, hotkey_name)
    keypair = load_keypair_from_file(filepath, password)
    await poll_redis_for_message_to_sign(redis_db, keypair)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting...")
