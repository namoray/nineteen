from datetime import datetime
import unittest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import BaseModel
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import asyncio

from fibre.miner.core.models.encryption import SymmetricKeyExchange
from fibre.miner.security.encryption import decrypt_symmetric_key_exchange_payload, decrypt_general_payload


class TestModel(BaseModel):
    field: str


class TestEncryption(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.config_mock = Mock()
        self.config_mock.encryption_keys_handler.private_key = self.private_key

    @patch("raycoms.miner.security.encryption.get_config")
    async def test_decrypt_symmetric_key_exchange(self, mock_get_config):
        mock_get_config.return_value = self.config_mock

        test_data = SymmetricKeyExchange(
            encrypted_symmetric_key="encrypted_key",
            symmetric_key_uuid="test-uuid",
            ss58_address="test-hotkey",
            timestamp=datetime.now().timestamp(),
            nonce="test-nonce",
            signature="test-signature",
        )
        encrypted_payload = self.private_key.public_key().encrypt(
            test_data.model_dump_json().encode(),
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
        )

        result = await decrypt_symmetric_key_exchange_payload(self.config_mock, encrypted_payload)

        self.assertIsInstance(result, SymmetricKeyExchange)
        self.assertEqual(result.symmetric_key_uuid, test_data.symmetric_key_uuid)
        self.assertEqual(result.encrypted_symmetric_key, test_data.encrypted_symmetric_key)
        self.assertEqual(result.ss58_address, test_data.ss58_address)
        self.assertEqual(result.nonce, test_data.nonce)
        self.assertEqual(result.signature, test_data.signature)

    @patch("raycoms.miner.security.encryption.Config")
    def test_decrypt_general_payload(self, mock_config):
        symmetric_key = Fernet.generate_key()
        f = Fernet(symmetric_key)

        test_data = TestModel(field="test")
        encrypted_payload = f.encrypt(test_data.model_dump_json().encode())

        mock_config.encryption_keys_handler.get_symmetric_key.return_value = symmetric_key

        result = decrypt_general_payload(TestModel, encrypted_payload, "test-uuid", "test-hotkey")

        self.assertIsInstance(result, TestModel)
        self.assertEqual(result.field, test_data.field)

    @patch("raycoms.miner.security.encryption.Config")
    def test_decrypt_general_payload_no_key(self, mock_config):
        mock_config.encryption_keys_handler.get_symmetric_key.return_value = None

        with self.assertRaises(HTTPException) as context:
            decrypt_general_payload(TestModel, b"test", "test-uuid", "test-hotkey")

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.detail, "No symmetric key found for that hotkey and uuid")


if __name__ == "__main__":
    asyncio.run(unittest.main())
