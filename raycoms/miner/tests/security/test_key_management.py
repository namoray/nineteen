import unittest
from unittest.mock import patch, mock_open
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from raycoms.miner.core.config import _derive_key_from_string
from raycoms.miner.security.nonce_management import NonceManager
from raycoms.miner.security.key_management import EncryptionKeysHandler
from raycoms.miner.core import miner_constants as mcst
from raycoms.miner.core.models.encryption import SymmetricKeyInfo


class TestKeyHandler(unittest.TestCase):
    def setUp(self):
        self.nonce_manager = NonceManager()
        self.hotkey = "test_hotkey"
        self.storage_encryption_key = _derive_key_from_string(mcst.DEFAULT_ENCRYPTION_STRING)
        self.encryption_keys_handler = EncryptionKeysHandler(self.nonce_manager, self.hotkey, self.storage_encryption_key)

    def test_init(self):
        self.assertIsInstance(self.encryption_keys_handler.fernet, Fernet)
        self.assertIsInstance(self.encryption_keys_handler.symmetric_keys, dict)
        self.assertIsInstance(self.encryption_keys_handler.private_key, rsa.RSAPrivateKey)
        self.assertIsInstance(self.encryption_keys_handler.public_key, rsa.RSAPublicKey)
        self.assertIsInstance(self.encryption_keys_handler.public_bytes, bytes)

    def test_add_and_get_symmetric_key(self):
        uuid = "test_uuid"
        symmetric_key = b"test_key"
        self.encryption_keys_handler.add_symmetric_key(uuid, self.hotkey, symmetric_key)
        retrieved_key = self.encryption_keys_handler.get_symmetric_key(self.hotkey, uuid)
        self.assertEqual(retrieved_key, symmetric_key)

    def test_get_nonexistent_symmetric_key(self):
        retrieved_key = self.encryption_keys_handler.get_symmetric_key("nonexistent_hotkey", "nonexistent_uuid")
        self.assertIsNone(retrieved_key)

    def test_clean_expired_keys(self):
        expired_key = SymmetricKeyInfo(b"expired", datetime.now() - timedelta(seconds=1))
        valid_key = SymmetricKeyInfo(b"valid", datetime.now() + timedelta(seconds=300))
        self.encryption_keys_handler.symmetric_keys = {
            "hotkey1": {"uuid1": expired_key, "uuid2": valid_key},
            "hotkey2": {"uuid3": expired_key},
        }
        self.encryption_keys_handler._clean_expired_keys()
        self.assertEqual(self.encryption_keys_handler.symmetric_keys, {"hotkey1": {"uuid2": valid_key}})

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", return_value=True)
    def test_save_and_load_symmetric_keys(self, mock_exists, mock_file):
        test_keys = {
            "hotkey1": {"uuid1": SymmetricKeyInfo(b"key1", datetime.now() + timedelta(seconds=300))},
            "hotkey2": {"uuid2": SymmetricKeyInfo(b"key2", datetime.now() + timedelta(seconds=300))},
        }
        self.encryption_keys_handler.symmetric_keys = test_keys

        self.encryption_keys_handler.save_symmetric_keys()

        mock_file().write.assert_called_once()
        encrypted_data = mock_file().write.call_args[0][0]

        mock_file().read.return_value = encrypted_data

        self.encryption_keys_handler.symmetric_keys = {}
        self.encryption_keys_handler.load_symmetric_keys()

        for hotkey, keys in self.encryption_keys_handler.symmetric_keys.items():
            for uuid, key_info in keys.items():
                self.assertIsInstance(key_info, SymmetricKeyInfo)
                self.assertEqual(key_info.key, test_keys[hotkey][uuid].key)

    @patch("os.path.exists", return_value=False)
    def test_load_symmetric_keys_file_not_exists(self, mock_exists):
        self.encryption_keys_handler.load_symmetric_keys()
        self.assertEqual(self.encryption_keys_handler.symmetric_keys, {})

    def test_load_asymmetric_keys(self):
        self.encryption_keys_handler.load_asymmetric_keys()
        self.assertIsInstance(self.encryption_keys_handler.private_key, rsa.RSAPrivateKey)
        self.assertIsInstance(self.encryption_keys_handler.public_key, rsa.RSAPublicKey)
        self.assertIsInstance(self.encryption_keys_handler.public_bytes, bytes)

    @patch.object(EncryptionKeysHandler, "save_symmetric_keys")
    def test_close(self, mock_save):
        self.encryption_keys_handler.close()
        mock_save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
