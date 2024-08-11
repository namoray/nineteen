from fiber.miner.core.config import factory_config
from fiber.miner import server
from miner.endpoints.subnet import factory_router as subnet_factory_router


app = server.factory_app(scalar_doc=True)

# To load & cache config
factory_config()
subnet_router = subnet_factory_router()
app.include_router(subnet_router)


if __name__ == "__main__":
    import uvicorn

    # Caching some configuration

    uvicorn.run(app, host="127.0.0.1", port=7999)
