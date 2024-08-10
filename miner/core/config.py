from functools import lru_cache

from miner.security import nonce_management
from dotenv import load_dotenv
import os
from miner.core.models.config import Config
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# Have this path passed in?
load_dotenv(dotenv_path=".miner.env", verbose=True)


def _derive_key_from_string(input_string: str, salt: bytes = b"salt_") -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(input_string.encode()))
    return key.decode()


@lru_cache
def factory_config() -> Config:
    from miner.security import key_management

    nonce_manager = nonce_management.NonceManager()
    hotkey = "TODO: ALLOW THIS TO BE PASSED IN SOMEHOW"
    storage_encryption_key = os.getenv("STORAGE_ENCRYPTION_KEY")
    if storage_encryption_key is None:
        storage_encryption_key = _derive_key_from_string(storage_encryption_key)
    key_handler = key_management.KeyHandler(nonce_manager, hotkey, storage_encryption_key)
    return Config(key_handler)
