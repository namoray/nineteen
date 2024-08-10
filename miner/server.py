"""
TODO:
- SAVE SYMMETRIC ON EXIT. USE A PASSWORD TO ENCRYPT, PASSED IN VIA AN ENV VAR
- PUT A TTL ON THE SYMMETRIC KEYS. AFTER THAT, THEY CANNOT BE USED. SAY, 3 HOURS.
- WRAP INTO GENERIC VALIDATOR AND MINER METHODS / FILES, BUT KEEP IT FUNCTIONAL. SHOULD BE QUITE EASY
- ADD THE VERIFY AND SIGNING METHODS
- ADD A 'POST DETAILS TO CHAIN' METHOD FOR MINERS TO POST THEIR AXON DETAILS TO THE CHAIN
- INTEGRATE THIS NEW WAY OF DOING THINGS INTO THE SUBNET CODE, BYE BYE SYNAPSES AND DENDRITES
"""

import base64
from functools import partial
import json
import time
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from fastapi import Request, Header
from typing import TypeVar, Type
from miner.config import Config
from miner.dependencies import get_config
from models import base_models

app = FastAPI()


def sign(message: str) -> str:
    # TODO: IMPLEMENT WITH SUBSTRATE INTERFACE
    return message


def verify_signature(message: str, hotkey: str, signature: str) -> bool:
    # TODO: Implement!
    return True


class SymmetricKeyExchange(BaseModel):
    encrypted_symmetric_key: str
    symmetric_key_uuid: str
    hotkey: str
    timestamp: float
    nonce: str
    signature: str


class PublicKeyResponse(BaseModel):
    public_key: str
    timestamp: float
    hotkey: str
    signature: str


T = TypeVar("T", bound=BaseModel)


@app.get("/public_key")
async def get_public_key(config: Config = Depends(get_config)):
    return PublicKeyResponse(
        public_key=config.key_handler.public_bytes.decode(),
        timestamp=time.time(),
        hotkey=config.key_handler.hotkey,
        signature=sign(f"{time.time()}{config.key_handler.hotkey}"),
    )


async def get_body(request: Request) -> bytes:
    return await request.body()


async def decrypt_symmetric_key_exchange(
    config: Config = Depends(get_config), encrypted_payload: bytes = Depends(get_body)
):
    decrypted_data = config.key_handler.private_key.decrypt(
        encrypted_payload,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )

    data_dict = json.loads(decrypted_data.decode())
    return SymmetricKeyExchange(**data_dict)


def decrypt_general_payload(
    model: Type[T],
    config: Config = Depends(get_config),
    encrypted_payload: bytes = Depends(get_body),
    key_uuid: str = Header(...),
    hotkey: str = Header(...),
) -> T:
    print(Config.key_handler.symmetric_keys)
    symmetric_key = Config.key_handler.get_symmetric_key(hotkey, key_uuid)
    if not symmetric_key:
        raise HTTPException(status_code=404, detail="No symmetric key found for that hotkey and uuid")

    f = Fernet(symmetric_key)
    print("Encrypted payload type: ", type(encrypted_payload))
    decrypted_data = f.decrypt(encrypted_payload)

    data_dict = json.loads(decrypted_data.decode())
    return model(**data_dict)


@app.post("/text-to-speech")
async def text_to_speech_endpoint(
    decrypted_payload: base_models.TextToSpeechRequest = Depends(
        partial(decrypt_general_payload, base_models.TextToSpeechRequest)
    ),
):
    print(decrypted_payload)
    return {"status": "Text-to-speech request received"}


@app.post("/exchange_symmetric_key")
async def exchange_symmetric_key(payload: SymmetricKeyExchange, config: Config = Depends(get_config)):
    if not verify_signature(
        message=f"{payload.timestamp}{payload.hotkey}",
        hotkey=payload.hotkey,
        signature=payload.signature,
    ):
        raise HTTPException(status_code=400, detail="Oi, invalid signature, you're not who you said you were!")
    if config.key_handler.nonce_manager.nonce_in_nonces(payload.nonce):
        raise HTTPException(
            status_code=400, detail="Oi, I've seen that nonce before. Don't send me the nonce more than once"
        )

    config.key_handler.nonce_manager.add_nonce(payload.nonce)

    # Decrypt the symmetric key
    encrypted_symmetric_key = base64.b64decode(payload.encrypted_symmetric_key)
    decrypted_symmetric_key = config.key_handler.private_key.decrypt(
        encrypted_symmetric_key,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )
    base64_symmetric_key = base64.b64encode(decrypted_symmetric_key).decode()
    config.key_handler.add_symmetric_key(payload.symmetric_key_uuid, payload.hotkey, base64_symmetric_key)

    return {"status": "Symmetric key exchanged successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=7999)
