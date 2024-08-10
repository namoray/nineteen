from dataclasses import dataclass
from functools import lru_cache
from miner import key_management
from miner import nonce_management
from dotenv import load_dotenv
import os

# Have this path passed in?
load_dotenv(dotenv_path=".miner.env", verbose=True)

@dataclass
class Config:
    key_handler: key_management.KeyHandler

@lru_cache
def factory_config() -> Config:
    nonce_manager = nonce_management.NonceManager()
    hotkey = "TODO: ALLOW THIS TO BE PASSED IN SOMEHOW"
    storage_encryption_key = os.getenv("STORAGE_ENCRYPTION_KEY", "")
    key_handler = key_management.KeyHandler(nonce_manager, hotkey, storage_encryption_key)
    return Config(key_handler)
