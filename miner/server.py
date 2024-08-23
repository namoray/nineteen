from fastapi import Request, Response
from fiber.miner import server
from miner.endpoints.subnet import factory_router as subnet_factory_router
from fiber.logging_utils import get_logger

logger = get_logger(__name__)

# This allows you to use uvicorn to run the server directly from the command line
app = server.factory_app(debug=True)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response: Response = await call_next(request)
    logger.info(f"Response: Status {response.status_code}")
    if response.status_code != 200:
        logger.error(f"Response error content: {response}")
    return response


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    logger.error(f"An error occurred: {exc}", exc_info=True)
    return {"detail": "Internal Server Error"}


subnet_router = subnet_factory_router()
app.include_router(subnet_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=7999)

    # uvicorn miner.server:app --reload --host 127.0.0.1 --port 7999 --env-file .1.env
