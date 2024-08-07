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
import threading
import time
from typing import Iterator
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding

from fastapi import Request, Header
from typing import TypeVar, Type
from models import base_models

app = FastAPI()


class NonceManager:
    def __init__(self) -> None:
        self._nonces: dict[str, float] = {}
        self.TTL: int = 60
        self._lock: threading.Lock = threading.Lock()
        self._running: bool = True
        self._cleanup_thread: threading.Thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self._cleanup_thread.start()

    def add_nonce(self, nonce: str) -> None:
        self._nonces[nonce] = time.time() + self.TTL

    def nonce_in_nonces(self, nonce: str) -> bool:
        with self._lock:
            expiry_time = self._nonces.get(nonce)
            if expiry_time is None:
                self.add_nonce(nonce)
                return False
            else:
                current_time = time.time()
                self._nonces[nonce] = current_time + self.TTL
                return True

    def cleanup(self) -> None:
        with self._lock:
            current_time = time.time()
            expired_nonces: list[str] = [
                nonce for nonce, expiry_time in self._nonces.items() if current_time > expiry_time
            ]
            for nonce in expired_nonces:
                del self._nonces[nonce]

    def _periodic_cleanup(self) -> None:
        while self._running:
            time.sleep(65)  # Sleep for 65 seconds (1 minute + 5 seconds)
            self.cleanup()

    def __contains__(self, nonce: str) -> bool:
        return self.nonce_in_nonces(nonce)

    def __len__(self) -> int:
        return len(self._nonces)

    def __iter__(self) -> Iterator[str]:
        return iter(self._nonces.keys())

    def shutdown(self) -> None:
        self._running = False
        self._cleanup_thread.join()


class KeyHandler:
    def __init__(self):
        self.symmetric_keys: dict[str, dict[str, bytes]] = {}
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()
        self.public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.nonce_manager = NonceManager()

    def add_symmetric_key(self, uuid: str, hotkey: str, symmetric_key: bytes) -> None:
        self.symmetric_keys[hotkey] = {uuid: symmetric_key}

    def get_symmetric_key(self, hotkey: str, uuid: str) -> bytes | None:
        return self.symmetric_keys.get(hotkey, {}).get(uuid)


key_handler = KeyHandler()
hotkey = "TODO: LOAD FROM ENV"


def sign(message: str) -> str:
    # TODO: IMPLEMENT WITH SUBSTRATE INTERFACE
    return message


def verify_signature(message: str, hotkey: str, signature: str) -> bool:
    # TODO: Implement!
    return True


def get_key_handler() -> KeyHandler:
    return key_handler


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
async def get_public_key():
    return PublicKeyResponse(
        public_key=key_handler.public_bytes.decode(),
        timestamp=time.time(),
        hotkey=hotkey,
        signature=sign(f"{time.time()}{hotkey}"),
    )


async def get_body(request: Request) -> bytes:
    return await request.body()


async def decrypt_symmetric_key_exchange(encrypted_payload: bytes = Depends(get_body)):
    decrypted_data = key_handler.private_key.decrypt(
        encrypted_payload,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )

    data_dict = json.loads(decrypted_data.decode())
    return SymmetricKeyExchange(**data_dict)


def decrypt_general_payload(
    model: Type[T],
    key_handler: KeyHandler = Depends(get_key_handler),
    encrypted_payload: bytes = Depends(get_body),
    key_uuid: str = Header(...),
    hotkey: str = Header(...),
) -> T:
    print(key_handler.symmetric_keys)
    symmetric_key = key_handler.get_symmetric_key(hotkey, key_uuid)
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
async def exchange_symmetric_key(payload: SymmetricKeyExchange):
    if not verify_signature(
        message=f"{payload.timestamp}{payload.hotkey}",
        hotkey=payload.hotkey,
        signature=payload.signature,
    ):
        raise HTTPException(status_code=400, detail="Oi, invalid signature, you're not who you said you were!")
    if key_handler.nonce_manager.nonce_in_nonces(payload.nonce):
        raise HTTPException(
            status_code=400, detail="Oi, I've seen that nonce before. Don't send me the nonce more than once"
        )

    key_handler.nonce_manager.add_nonce(payload.nonce)

    # Decrypt the symmetric key
    encrypted_symmetric_key = base64.b64decode(payload.encrypted_symmetric_key)
    decrypted_symmetric_key = key_handler.private_key.decrypt(
        encrypted_symmetric_key,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )
    base64_symmetric_key = base64.b64encode(decrypted_symmetric_key).decode()
    key_handler.add_symmetric_key(payload.symmetric_key_uuid, payload.hotkey, base64_symmetric_key)

    return {"status": "Symmetric key exchanged successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=7999)
