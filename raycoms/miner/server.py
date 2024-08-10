"""
TODO:
- WRAP INTO GENERIC VALIDATOR AND MINER METHODS / FILES, BUT KEEP IT FUNCTIONAL. SHOULD BE QUITE EASY
- Add metagraph for miner so it can check validators are in the metagraph and their stake
- add the blacklist functionality. Middleware?
- MAKE SURE we have a standard way to veirfy and construct message signatures
- ADD A 'POST DETAILS TO CHAIN' METHOD FOR MINERS TO POST THEIR AXON DETAILS TO THE CHAIN
- INTEGRATE THIS NEW WAY OF DOING THINGS INTO THE SUBNET CODE, BYE BYE SYNAPSES AND DENDRITES
- SINGING SERVICE NOW ONLY NEEDS TO SIGN THESE INITIAL MESSAGES - CAN ADD THAT INTO THE CODE
- SIGNING SERVICE FOR WEIGHT SETTING NEEDS A BIT OF A REWORK
- THEN TEST motha
"""

from fastapi import FastAPI
from raycoms.miner.endpoints.subnet import factory_router as subnet_factory_router
from raycoms.miner.endpoints.handshake import factory_router as handshake_factory_router
from raycoms.miner.core.config import factory_config

def factory_app() -> FastAPI:
    app = FastAPI()

    subnet_router = subnet_factory_router()
    handshake_router = handshake_factory_router()
    app.include_router(subnet_router)
    app.include_router(handshake_router)

    return app


if __name__ == "__main__":
    import uvicorn

    app = factory_app()

    # Caching some configuration
    factory_config()

    uvicorn.run(app, host="127.0.0.1", port=7999)
