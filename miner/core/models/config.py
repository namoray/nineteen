from dataclasses import dataclass
from miner.security import key_management


@dataclass
class Config:
    key_handler: key_management.KeyHandler
