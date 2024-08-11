"""
TODO:
- Add metagraph for miner so it can check validators are in the metagraph and their stake
- add the blacklist functionality. Middleware?
- ADD A 'POST DETAILS TO CHAIN' METHOD FOR MINERS TO POST THEIR AXON DETAILS TO THE CHAIN
- INTEGRATE THIS NEW WAY OF DOING THINGS INTO THE SUBNET CODE, BYE BYE SYNAPSES AND DENDRITES
- BIN SIGNING SERVICE AND BAKE ALL THIS INTO THE SUBNET
- THEN TEST motha
"""

from fastapi import FastAPI
from fiber.miner.endpoints.handshake import factory_router as handshake_factory_router
from scalar_fastapi import get_scalar_api_reference


def factory_app(scalar_doc: bool = True) -> FastAPI:
    app = FastAPI()

    if scalar_doc:

        async def scalar_html():
            return get_scalar_api_reference(openapi_url=app.openapi_url, title=app.title)

        app.add_api_route("/doc", scalar_html, include_in_schema=False)

    handshake_router = handshake_factory_router()
    app.include_router(handshake_router)

    return app
