"""
TODO:
- PUT A TTL ON THE SYMMETRIC KEYS. AFTER THAT, THEY CANNOT BE USED. SAY, 3 HOURS.
- WRAP INTO GENERIC VALIDATOR AND MINER METHODS / FILES, BUT KEEP IT FUNCTIONAL. SHOULD BE QUITE EASY
- ADD THE VERIFY AND SIGNING METHODS
- NONCES should also be numbers which are always bigger than the current hour we are in or something.
- So expired nonces can be very easily rejected without having to store UUIDS
- ADD A 'POST DETAILS TO CHAIN' METHOD FOR MINERS TO POST THEIR AXON DETAILS TO THE CHAIN
- INTEGRATE THIS NEW WAY OF DOING THINGS INTO THE SUBNET CODE, BYE BYE SYNAPSES AND DENDRITES
- SINGING SERVICE NOW ONLY NEEDS TO SIGN THESE INITIAL MESSAGES - CAN ADD THAT INTO THE CODE
- SIGNING SERVICE FOR WEIGHT SETTING NEEDS A BIT OF A REWORK
- THEN TEST motha
"""

from fastapi import FastAPI
from miner.endpoints.subnet import factory_router as subnet_factory_router
from miner.endpoints.handshake import factory_router as handshake_factory_router


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
    uvicorn.run(app, host="127.0.0.1", port=7999)
