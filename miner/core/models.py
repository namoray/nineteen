from pydantic import BaseModel
from dataclasses import dataclass
from miner.security import key_management


@dataclass
class Config:
    key_handler: key_management.KeyHandler


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
