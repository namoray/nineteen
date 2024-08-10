import base64
import time
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from raycoms.miner.core.config import Config
from raycoms.miner.core.dependencies import get_config
from raycoms.miner.core.models.encryption import PublicKeyResponse, SymmetricKeyExchange
from raycoms.miner.security import signatures

app = FastAPI()


@app.get("/public_key")
async def get_public_key(config: Config = Depends(get_config)):
    return PublicKeyResponse(
        public_key=config.encryption_keys_handler.public_bytes.decode(),
        timestamp=time.time(),
        hotkey=config.encryption_keys_handler.hotkey,
        signature=signatures.sign_message(f"{time.time()}{config.encryption_keys_handler.hotkey}"),
    )


@app.post("/exchange_symmetric_key")
async def exchange_symmetric_key(payload: SymmetricKeyExchange, config: Config = Depends(get_config)):
    if not signatures.verify_signature(
        message=f"{payload.timestamp}{payload.hotkey}",
        hotkey=payload.hotkey,
        signature=payload.signature,
    ):
        raise HTTPException(status_code=400, detail="Oi, invalid signature, you're not who you said you were!")
    if config.encryption_keys_handler.nonce_manager.nonce_in_nonces(payload.nonce):
        raise HTTPException(
            status_code=400, detail="Oi, I've seen that nonce before. Don't send me the nonce more than once"
        )

    config.encryption_keys_handler.nonce_manager.add_nonce(payload.nonce)
    encrypted_symmetric_key = base64.b64decode(payload.encrypted_symmetric_key)
    decrypted_symmetric_key = config.encryption_keys_handler.private_key.decrypt(
        encrypted_symmetric_key,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )
    base64_symmetric_key = base64.b64encode(decrypted_symmetric_key).decode()
    config.encryption_keys_handler.add_symmetric_key(payload.symmetric_key_uuid, payload.hotkey, base64_symmetric_key)

    return {"status": "Symmetric key exchanged successfully"}


def factory_router() -> APIRouter:
    router = APIRouter()
    router.add_api_route("/exchange_symmetric_key", exchange_symmetric_key, tags=["handshake"])
    router.add_api_route("/public_key", get_public_key, tags=["handshake"])
    return router