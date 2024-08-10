
from pydantic import BaseModel


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
