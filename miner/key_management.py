from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from miner.nonce_management import NonceManager


class KeyHandler:
    def __init__(self, nonce_manager: NonceManager, hotkey: str):
        self.symmetric_keys: dict[str, dict[str, bytes]] = {}
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()
        self.public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.hotkey = hotkey
        self.nonce_manager = nonce_manager

    def add_symmetric_key(self, uuid: str, hotkey: str, symmetric_key: bytes) -> None:
        self.symmetric_keys[hotkey] = {uuid: symmetric_key}

    def get_symmetric_key(self, hotkey: str, uuid: str) -> bytes | None:
        return self.symmetric_keys.get(hotkey, {}).get(uuid)
