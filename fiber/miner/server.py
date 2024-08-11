"""
TODO:
- Miners to store the fernet keys instead of symmetric keys
- ADD A 'POST DETAILS TO CHAIN' METHOD FOR MINERS TO POST THEIR AXON DETAILS TO THE CHAIN
- INTEGRATE THIS NEW WAY OF DOING THINGS INTO THE SUBNET CODE, BYE BYE SYNAPSES AND DENDRITES
- BIN SIGNING SERVICE AND BAKE ALL THIS INTO THE SUBNET
- THEN TEST motha
"""

from contextlib import asynccontextmanager
import threading
from fastapi import FastAPI
from fiber.miner.endpoints.handshake import factory_router as handshake_factory_router
from fiber.miner.core import configuration
from scalar_fastapi import get_scalar_api_reference
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


def factory_app(scalar_doc: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = configuration.factory_config()
        metagraph = config.metagraph
        sync_thread = threading.Thread(target=metagraph.periodically_sync_nodes, daemon=True)
        sync_thread.start()

        yield

        logger.info("Shutting down...")

        metagraph.shutdown()
        sync_thread.join()

    app = FastAPI(lifespan=lifespan)

    if scalar_doc:

        async def scalar_html():
            return get_scalar_api_reference(openapi_url=app.openapi_url, title=app.title)

        app.add_api_route("/doc", scalar_html, include_in_schema=False)

    handshake_router = handshake_factory_router()
    app.include_router(handshake_router)

    return app
