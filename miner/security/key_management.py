import json
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.fernet import Fernet
from miner.security.nonce_management import NonceManager
from miner.core import miner_constants as mcst


class KeyHandler:
    def __init__(self, nonce_manager: NonceManager, hotkey: str, storage_encryption_key: str):
        self.hotkey = hotkey
        self.nonce_manager = nonce_manager
        self.fernet = Fernet(storage_encryption_key)
        self.symmetric_keys: dict[str, dict[str, bytes]] = {}
        self.load_asymmetric_keys()
        self.load_symmetric_keys()

    def add_symmetric_key(self, uuid: str, hotkey: str, symmetric_key: bytes) -> None:
        if hotkey not in self.symmetric_keys:
            self.symmetric_keys[hotkey] = {}
        self.symmetric_keys[hotkey][uuid] = symmetric_key

    def get_symmetric_key(self, hotkey: str, uuid: str) -> bytes | None:
        return self.symmetric_keys.get(hotkey, {}).get(uuid)

    def save_symmetric_keys(self) -> None:
        serializable_keys = {
            hotkey: {uuid: key.hex() for uuid, key in keys.items()} for hotkey, keys in self.symmetric_keys.items()
        }
        json_data = json.dumps(serializable_keys)
        encrypted_data = self.fernet.encrypt(json_data.encode())

        with open(mcst.SYMMETRIC_KEYS_FILENAME, "wb") as file:
            file.write(encrypted_data)

    def load_symmetric_keys(self) -> None:
        if os.path.exists(mcst.SYMMETRIC_KEYS_FILENAME):
            with open(mcst.SYMMETRIC_KEYS_FILENAME, "rb") as f:
                encrypted_data = f.read()
            decrypted_data = self.fernet.decrypt(encrypted_data)
            loaded_keys: dict[str, dict[str, str]] = json.loads(decrypted_data.decode())
            self.symmetric_keys = {
                hotkey: {uuid: bytes.fromhex(key) for uuid, key in keys.items()} for hotkey, keys in loaded_keys.items()
            }

    def load_asymmetric_keys(self) -> None:
        # TODO: Allow this to be passed in via env too
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()
        self.public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def close(self) -> None:
        self.save_symmetric_keys()
