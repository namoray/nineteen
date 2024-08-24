# TODO: Do we need connection pools with redis?
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from validator.entry_node.src.endpoints.text import router as chat_router
from validator.entry_node.src.core import configuration
from core.logging import get_logger

logger = get_logger(__name__)


def factory_app(debug: bool = False) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await configuration.factory_config()  # Cachin'
        yield

        logger.info("Shutting down...")

    app = FastAPI(lifespan=lifespan, debug=debug)
    return app


app = factory_app()
app.include_router(chat_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

    # uvicorn validator.entry_node.src.server:app --reload --host 127.0.0.1 --port 8000 --env-file .dev.env
