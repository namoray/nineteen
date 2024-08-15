from fiber.miner import server
from miner.endpoints.subnet import factory_router as subnet_factory_router

# This allows you to use uvicorn to run the server directly from the command line
app = server.factory_app(debug=True)

subnet_router = subnet_factory_router()
app.include_router(subnet_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=7999)

    # uvicorn miner.server:app --reload --host 127.0.0.1 --port 7999 --env-file .1.env
