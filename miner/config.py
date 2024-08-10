from dataclasses import dataclass
from functools import lru_cache
from miner import key_management
from miner import nonce_management


@dataclass
class Config:
    key_handler: key_management.KeyHandler

@lru_cache
def factory_config() -> Config:
    nonce_manager = nonce_management.NonceManager()
    hotkey = "TODO: ALLOW THIS TO BE PASSED IN SOMEHOW"
    key_handler = key_management.KeyHandler(nonce_manager, hotkey)
    return Config(key_handler)
