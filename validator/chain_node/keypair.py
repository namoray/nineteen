import asyncio
import json
from typing import Any
from substrateinterface import Keypair
from substrateinterface.keypair import KeypairType
from redis import Redis
from validator.utils import redis_utils as rutils, redis_constants as rcst
import uuid
from core.logging import get_logger


logger = get_logger(__name__)


def _construct_signed_message_key(job_id: str) -> str:
    return f"{rcst.SIGNED_MESSAGES_KEY}:{job_id}"


class RedisGappedKeypair(Keypair):
    """
    Overwrite the sign method so we don't need private keys on this box
    """

    def __init__(
        self,
        redis_db: Redis,
        ss58_address: str = None,
        ss58_format: int = None,
        public_key: bytes | str = None,
        crypto_type: int = KeypairType.SR25519,
    ):
        super().__init__(
            ss58_address=ss58_address, public_key=public_key, ss58_format=ss58_format, crypto_type=crypto_type
        )

        self.redis_db = redis_db

    def sign(self, data: Any) -> bytes:
        logger.debug("Signing message with keypair!")

        job_id = str(uuid.uuid4())
        payload = {
            rcst.MESSAGE: data,
            rcst.JOB_ID: job_id,
        }

        json_to_add = rutils._remove_enums(payload)
        json_string = json.dumps(json_to_add)
        self.redis_db.rpush(rcst.SIGNING_WEIGHTS_QUEUE_KEY, json_string)

        logger.debug(f"Added payload to signing queue: {payload}. Now waiting for signed payload")

        job_results_key = _construct_signed_message_key(job_id)

        signed_payload_raw = self.redis_db.blpop(job_results_key, timeout=10)
        if signed_payload_raw is None:
            raise TimeoutError("Timed out waiting for signed payload")

        logger.debug(f"Got signed payload: {signed_payload_raw}")

        signed_payload = json.loads(signed_payload_raw[1].decode("utf-8"))
        signature = signed_payload[rcst.SIGNATURE]
        logger.debug(f"Got signature: {signature}")
        return signature


async def main():
    redis_db = Redis(host="redis")
    keypair = RedisGappedKeypair(redis_db=redis_db, ss58_address="5Hddm3iBFD2GLT5ik7LZnT3XJUnRnN8PoeCFgGQgawUVKNm8")

    logger.warn("Signing message, please make sure the signing service is already running")
    keypair.sign("hello world")


if __name__ == "__main__":
    asyncio.run(main())
