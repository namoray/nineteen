import json
import uuid

import aiohttp
from redis.asyncio import Redis
from core.logging import get_logger
from dataclasses import dataclass
import base64

logger = get_logger(__name__)

### NOTE: This is repeated throughout, how to better organise?
SIGNING_WEIGHTS_QUEUE_KEY = "SIGNING_WEIGHTS_QUEUE"
SIGNED_MESSAGES_KEY = "SIGNED_MESSAGES"


@dataclass
class SigningPayload:
    message: bytes | str
    job_id: str
    is_b64encoded: bool

    def to_dict(self):
        if isinstance(self.message, bytes):
            return {
                "message": base64.b64encode(self.message).decode("utf-8"),
                "job_id": self.job_id,
                "is_b64encoded": True,
            }
        elif isinstance(self.message, str):
            return {"message": self.message, "job_id": self.job_id, "is_b64encoded": False}
        else:
            raise TypeError("message must be either bytes or str")

    @classmethod
    def from_dict(cls, data):
        is_b64encoded = data["is_b64encoded"]
        message = data["message"]
        if is_b64encoded:
            message = base64.b64decode(message)
        return cls(message=message, job_id=data["job_id"], is_b64encoded=is_b64encoded)


@dataclass
class SignedPayload:
    signature: str
    job_id: str


def _construct_signed_message_key(job_id: str) -> str:
    return f"{SIGNED_MESSAGES_KEY}:{job_id}"


### END OF NOTE


class dendrite:
    def __init__(self, redis_db: Redis) -> None:
        # Unique identifier for the instance
        self.uuid = str(uuid.uuid1())

        self.synapse_history: list = []

        self._session: aiohttp.ClientSession | None = None
        self.redis_db = redis_db

    @property
    async def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0))
        return self._session

    async def _sign_mesage(self, message: str) -> str:
        job_id = str(uuid.uuid4())
        await self.redis_db.rpush(
            SIGNING_WEIGHTS_QUEUE_KEY,
            json.dumps(SigningPayload(message=message, job_id=job_id, is_b64encoded=False).to_dict()),
        )

        job_results_key = _construct_signed_message_key(job_id)

        resp = await self.redis_db.blpop(job_results_key, 10)
        if resp is None:
            raise Exception("Timed out waiting for signed message")

        _, payload_raw = resp

        payload = SignedPayload(**json.loads(payload_raw))

        return payload.signature
