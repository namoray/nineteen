import json
from typing import Any
import aiohttp
from cryptography.hazmat.backends import default_backend
from beam.miner.core.models import encryption
from cryptography.hazmat.bindings._rust import openssl as rust_openssl
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
import time
import os
from beam.miner.security import signatures
import base64
from substrateinterface import Keypair
from beam.validator.security.encryption import public_key_encrypt
from beam import constants as bcst
from cryptography.fernet import Fernet


async def perform_handshake(
    aio_client: aiohttp.ClientSession,
    server_address: str,
    keypair: Keypair,
):
    public_key_encryption_key = await get_public_encryption_key(aio_client, server_address)

    symmetric_key: bytes = os.urandom(32)
    symmetric_key_uuid: str = os.urandom(16).hex()

    exchange_symmetric_key(
        server_address,
        keypair,
        public_key_encryption_key,
        symmetric_key,
        symmetric_key_uuid,
    )

    return symmetric_key, symmetric_key_uuid


async def get_public_encryption_key(
    aio_client: aiohttp.ClientSession, server_address: str, timeout: int = 3
) -> X25519PublicKey:
    async with aio_client.get(f"{server_address}/{bcst.PUBLIC_ENCRYPTION_KEY_ENDPOINT}", timeout=timeout) as response:
        if response.status == 200:
            data = encryption.PublicKeyResponse(**(await response.json()))
            public_key_pem = data.public_key.encode()
            public_key_encryption_key = rust_openssl.keys.load_pem_public_key(public_key_pem, backend=default_backend())
            return public_key_encryption_key
        else:
            raise Exception(f"Failed to get public key: {await response.text()}")


async def exchange_symmetric_key(
    aio_client: aiohttp.ClientSession,
    server_address: str,
    keypair: Keypair,
    public_key_encryption_key: X25519PublicKey,
    symmetric_key: bytes,
    symmetric_key_uuid: str,
    timeout: int = 3,
) -> bool:
    payload = {
        "encrypted_symmetric_key": base64.b64encode(
            public_key_encrypt(public_key_encryption_key, symmetric_key)
        ).decode("utf-8"),
        "symmetric_key_uuid": symmetric_key_uuid,
        "ss58_address": keypair.ss58_address,
        "timestamp": time.time(),
        "nonce": os.urandom(16).hex(),
        "signature": signatures.sign_message(keypair, signatures.construct_public_key_message_to_sign()),
    }

    async with aio_client.post(
        f"{server_address}/{bcst.EXCHANGE_SYMMETRIC_KEY_ENDPOINT}", json=payload, timeout=timeout
    ) as response:
        return response.status == 200


def get_encrypted_payload(
    server_address: str,
    client_ss58_address: str,
    fernet: Fernet,
    endpoint: str,
    payload: dict[str, Any],
    symmetric_key_uuid: str,
    timeout: int = 10,
) -> dict[str, Any]:
    encrypted_payload = fernet.encrypt(json.dumps(payload).encode())
    payload = {
        "url": f"{server_address}/{endpoint}",
        "data": encrypted_payload,
        "headers": {
            "Content-Type": "application/octet-stream",
            bcst.SYMMETRIC_KEY_UUID: symmetric_key_uuid,
            bcst.SS58_ADDRESS: client_ss58_address,
        },
        "timeout": timeout,
    }
    return payload
