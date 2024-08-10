from dataclasses import dataclass
from beam.miner.security import key_management
from substrateinterface import Keypair

@dataclass
class Config:
    encryption_keys_handler: key_management.EncryptionKeysHandler
    keypair: Keypair
