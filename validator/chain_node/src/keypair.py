import asyncio
import json
from typing import Union
from substrateinterface import Keypair
from substrateinterface.keypair import KeypairType
from redis import Redis
from validator.utils import redis_constants as rcst, redis_dataclasses as rdc
import uuid
from core.logging import get_logger
from scalecodec.base import ScaleBytes

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

    def sign(self, data: Union[ScaleBytes, bytes, str]) -> bytes:
        """
        For some reason bittensor gobbles up logging, and logging wont work in here :-(
        """

        if type(data) is ScaleBytes:
            data = bytes(data.data)
        elif data[0:2] == "0x":
            data = bytes.fromhex(data[2:])
        elif type(data) is str:  # noqa
            data = data.encode()

        # Use below to debug, since logging is hell when bittensor is involved :)
        # raise ValueError(f"Data: {data} not supported")

        job_id = str(uuid.uuid4())

        payload = rdc.SigningPayload(
            message=data,
            job_id=job_id,
            is_b64encoded=True,
        )
        json_string = json.dumps(payload.to_dict())

        self.redis_db.rpush(rcst.SIGNING_WEIGHTS_QUEUE_KEY, json_string)

        logger.debug(f"Added payload to signing queue: {payload}. Now waiting for signed payload")

        job_results_key = _construct_signed_message_key(job_id)

        signed_payload_raw = self.redis_db.blpop(job_results_key, timeout=10)

        if signed_payload_raw is None:
            raise TimeoutError("Timed out waiting for signed payload")
        signed_payload = rdc.SignedPayload(**json.loads(signed_payload_raw[1]))

        logger.debug(f"Got signed payload: {signed_payload}")
        signature = signed_payload.signature
        logger.debug(f"Got signature: {signature}")

        # signature is hex encoded, so get back to bytes
        return bytes.fromhex(signature[2:])


async def main():
    redis_db = Redis(host="redis")
    keypair = RedisGappedKeypair(redis_db=redis_db, ss58_address="5Hddm3iBFD2GLT5ik7LZnT3XJUnRnN8PoeCFgGQgawUVKNm8")

    logger.warning("Signing message, please make sure the signing service is already running")
    keypair.sign("hello world")


if __name__ == "__main__":
    asyncio.run(main())
