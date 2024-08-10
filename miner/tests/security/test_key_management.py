"""Definitely not AI generated"""
import unittest
from unittest.mock import patch, mock_open
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from miner.core.config import _derive_key_from_string
from miner.security.nonce_management import NonceManager
from miner.security.key_management import KeyHandler
from miner.core import miner_constants as mcst


class TestKeyHandler(unittest.TestCase):
    def setUp(self):
        self.nonce_manager = NonceManager()
        self.hotkey = "test_hotkey"
        self.storage_encryption_key = _derive_key_from_string(mcst.DEFAULT_ENCRYPTION_STRING)
        self.key_handler = KeyHandler(self.nonce_manager, self.hotkey, self.storage_encryption_key)

    def test_init(self):
        self.assertIsInstance(self.key_handler.fernet, Fernet)
        self.assertEqual(self.key_handler.hotkey, self.hotkey)
        self.assertIsInstance(self.key_handler.symmetric_keys, dict)
        self.assertIsInstance(self.key_handler.private_key, rsa.RSAPrivateKey)
        self.assertIsInstance(self.key_handler.public_key, rsa.RSAPublicKey)
        self.assertIsInstance(self.key_handler.public_bytes, bytes)

    def test_add_and_get_symmetric_key(self):
        uuid = "test_uuid"
        symmetric_key = b"test_key"
        self.key_handler.add_symmetric_key(uuid, self.hotkey, symmetric_key)
        retrieved_key = self.key_handler.get_symmetric_key(self.hotkey, uuid)
        self.assertEqual(retrieved_key, symmetric_key)

    def test_get_nonexistent_symmetric_key(self):
        retrieved_key = self.key_handler.get_symmetric_key("nonexistent_hotkey", "nonexistent_uuid")
        self.assertIsNone(retrieved_key)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=True)
    def test_save_and_load_symmetric_keys(self, mock_exists, mock_file):
        test_keys = {"hotkey1": {"uuid1": b"key1"}, "hotkey2": {"uuid2": b"key2"}}
        self.key_handler.symmetric_keys = test_keys
        
        self.key_handler.save_symmetric_keys()
        
        mock_file().write.assert_called_once()
        encrypted_data = mock_file().write.call_args[0][0]
        
        mock_file().read.return_value = encrypted_data
        
        self.key_handler.symmetric_keys = {}
        self.key_handler.load_symmetric_keys()
        
        loaded_keys = {
            hotkey: {uuid: key.decode() if isinstance(key, bytes) else key 
                     for uuid, key in keys.items()}
            for hotkey, keys in self.key_handler.symmetric_keys.items()
        }
        expected_keys = {
            hotkey: {uuid: key.decode() if isinstance(key, bytes) else key 
                     for uuid, key in keys.items()}
            for hotkey, keys in test_keys.items()
        }
        
        self.assertEqual(loaded_keys, expected_keys)


    @patch("os.path.exists", return_value=False)
    def test_load_symmetric_keys_file_not_exists(self, mock_exists):
        self.key_handler.load_symmetric_keys()
        self.assertEqual(self.key_handler.symmetric_keys, {})

    def test_load_asymmetric_keys(self):
        self.key_handler.load_asymmetric_keys()
        self.assertIsInstance(self.key_handler.private_key, rsa.RSAPrivateKey)
        self.assertIsInstance(self.key_handler.public_key, rsa.RSAPublicKey)
        self.assertIsInstance(self.key_handler.public_bytes, bytes)

    @patch.object(KeyHandler, "save_symmetric_keys")
    def test_close(self, mock_save):
        self.key_handler.close()
        mock_save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
