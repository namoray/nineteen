from functools import lru_cache

from raycoms.miner.security import nonce_management
from dotenv import load_dotenv
import os
from raycoms.miner.core.models.config import Config
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import TypeVar
from raycoms.miner.security import key_management
from raycoms import keypair_utils
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
    nonce_manager = nonce_management.NonceManager()

    wallet_name = os.getenv("WALLET_NAME", "default")
    hotkey_name = os.getenv("HOTKEY_NAME", "default")

    filepath = keypair_utils.construct_wallet_path(wallet_name, hotkey_name)
    keypair = keypair_utils.load_keypair_from_file(filepath)

    hotkey = "TODO: ALLOW THIS TO BE PASSED IN SOMEHOW"
    storage_encryption_key = os.getenv("STORAGE_ENCRYPTION_KEY")
    if storage_encryption_key is None:
        storage_encryption_key = _derive_key_from_string(storage_encryption_key)
    encryption_keys_handler = key_management.EncryptionKeysHandler(nonce_manager, hotkey, storage_encryption_key)
    return Config(encryption_keys_handler=encryption_keys_handler, keypair=keypair)
