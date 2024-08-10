import json
from fastapi import Depends, HTTPException, Request
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi import Header
from typing import Type, TypeVar

from pydantic import BaseModel
from raycoms.miner.core.dependencies import get_config
from raycoms.miner.core.models.encryption import SymmetricKeyExchange
from raycoms.miner.core.models.config import Config


T = TypeVar("T", bound=BaseModel)


async def get_body(request: Request) -> bytes:
    return await request.body()


async def decrypt_symmetric_key_exchange(
    config: Config = Depends(get_config), encrypted_payload: bytes = Depends(get_body)
):
    decrypted_data = config.encryption_keys_handler.private_key.decrypt(
        encrypted_payload,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )

    data_dict = json.loads(decrypted_data.decode())
    return SymmetricKeyExchange(**data_dict)


def decrypt_general_payload(
    model: Type[T],
    encrypted_payload: bytes = Depends(get_body),
    key_uuid: str = Header(...),
    hotkey: str = Header(...),
) -> T:
    print(Config.encryption_keys_handler.symmetric_keys)
    symmetric_key = Config.encryption_keys_handler.get_symmetric_key(hotkey, key_uuid)
    if not symmetric_key:
        raise HTTPException(status_code=404, detail="No symmetric key found for that hotkey and uuid")

    f = Fernet(symmetric_key)
    print("Encrypted payload type: ", type(encrypted_payload))
    decrypted_data = f.decrypt(encrypted_payload)

    data_dict = json.loads(decrypted_data.decode())
    return model(**data_dict)
