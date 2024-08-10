from datetime import datetime
import json
import os
import threading
import time
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.fernet import Fernet
from fibre.miner.core.models.encryption import SymmetricKeyInfo
from fibre.miner.security.nonce_management import NonceManager
from fibre.miner.core import miner_constants as mcst


class EncryptionKeysHandler:
    def __init__(self, nonce_manager: NonceManager, hotkey: str, storage_encryption_key: str):
        self.nonce_manager = nonce_manager
        self.fernet = Fernet(storage_encryption_key)
        self.symmetric_keys: dict[str, dict[str, SymmetricKeyInfo]] = {}
        self.load_asymmetric_keys()
        self.load_symmetric_keys()

        self._running: bool = True
        self._cleanup_thread: threading.Thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self._cleanup_thread.start()

    def add_symmetric_key(self, uuid: str, hotkey: str, symmetric_key: bytes) -> None:
        symmetric_key_info = SymmetricKeyInfo.create(symmetric_key)
        if hotkey not in self.symmetric_keys:
            self.symmetric_keys[hotkey] = {}
        self.symmetric_keys[hotkey][uuid] = symmetric_key_info

    def get_symmetric_key(self, hotkey: str, uuid: str) -> SymmetricKeyInfo | None:
        return self.symmetric_keys.get(hotkey, {}).get(uuid)

    def save_symmetric_keys(self) -> None:
        serializable_keys = {
            hotkey: {
                uuid: {"key": key_info.key.hex(), "expiration_time": key_info.expiration_time.isoformat()}
                for uuid, key_info in keys.items()
            }
            for hotkey, keys in self.symmetric_keys.items()
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
                hotkey: {
                    uuid: SymmetricKeyInfo(
                        bytes.fromhex(key_data["key"]), datetime.fromisoformat(key_data["expiration_time"])
                    )
                    for uuid, key_data in keys.items()
                }
                for hotkey, keys in loaded_keys.items()
            }

    def _clean_expired_keys(self) -> None:
        for hotkey in list(self.symmetric_keys.keys()):
            self.symmetric_keys[hotkey] = {
                uuid: key_info for uuid, key_info in self.symmetric_keys[hotkey].items() if not key_info.is_expired()
            }
            if not self.symmetric_keys[hotkey]:
                del self.symmetric_keys[hotkey]

    def _periodic_cleanup(self) -> None:
        while self._running:
            self._clean_expired_keys()
            self.nonce_manager.cleanup_expired_nonces()
            time.sleep(65)

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
