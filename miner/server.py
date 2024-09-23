import os
from fiber.miner import server
from miner.endpoints.text import factory_router as text_factory_router
from miner.endpoints.image import factory_router as image_factory_router
from miner.endpoints.generic import factory_router as generic_factory_router
from core.log import get_logger
from fiber.miner.middleware import configure_extra_logging_middleware

logger = get_logger(__name__)

app = server.factory_app(debug=True)


text_router = text_factory_router()
image_router = image_factory_router()
generic_router = generic_factory_router()
app.include_router(text_router)
app.include_router(image_router)
app.include_router(generic_router)

if os.getenv("ENV", "prod").lower() == "dev":
    configure_extra_logging_middleware(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=7999)

    # uvicorn miner.server:app --reload --host 127.0.0.1 --port 7999 --env-file .1.env
