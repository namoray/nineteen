from datetime import datetime, timedelta
from pydantic import BaseModel
from dataclasses import dataclass


@dataclass
class SymmetricKeyInfo:
    key: bytes
    expiration_time: datetime

    @classmethod
    def create(cls, key: bytes, ttl_seconds: int = 60 * 60 * 5):
        return cls(key, datetime.now() + timedelta(seconds=ttl_seconds))

    def is_expired(self) -> bool:
        return datetime.now() > self.expiration_time


class SymmetricKeyExchange(BaseModel):
    encrypted_symmetric_key: str
    symmetric_key_uuid: str
    hotkey: str
    timestamp: float
    nonce: str
    signature: str


class PublicKeyResponse(BaseModel):
    public_key: str
    timestamp: float
    hotkey: str
    signature: str
