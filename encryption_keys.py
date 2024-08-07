import os
import sys
import base64
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv


def generate_key_pair() -> Tuple[X25519PrivateKey, bytes]:
    private_key = X25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return private_key, public_key


def save_keys_to_env(private_key: X25519PrivateKey, public_key: bytes, env_file_name: str) -> None:
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )

    private_b64: str = base64.b64encode(private_bytes).decode("utf-8")
    public_b64: str = base64.b64encode(public_key).decode("utf-8")

    with open(env_file_name, "w") as f:
        f.write(f"MINER_PRIVATE_KEY={private_b64}\n")
        f.write(f"MINER_PUBLIC_KEY={public_b64}\n")


def load_keys_from_env(env_file_name: str) -> Tuple[X25519PrivateKey, bytes]:
    load_dotenv(env_file_name, verbose=True)
    private_b64: str = os.getenv("MINER_PRIVATE_KEY")
    public_b64: str = os.getenv("MINER_PUBLIC_KEY")

    private_bytes: bytes = base64.b64decode(private_b64)
    public_bytes: bytes = base64.b64decode(public_b64)

    private_key = X25519PrivateKey.from_private_bytes(private_bytes)
    public_key = public_bytes

    return private_key, public_key


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python miner_server.py <env_file_name>")
        sys.exit(1)

    env_file_name: str = sys.argv[1]
    private_key, public_key = generate_key_pair()
    save_keys_to_env(private_key, public_key, env_file_name)
    print(f"Keys generated and saved to {env_file_name}")
