from fastapi import Request, Response  # noqa
from starlette.middleware.base import _StreamingResponse  # noqa
from fiber.miner import server
from miner.endpoints.text import factory_router as text_factory_router
from miner.endpoints.image import factory_router as image_factory_router
from miner.endpoints.generic import factory_router as generic_factory_router
from fiber.logging_utils import get_logger
logger = get_logger(__name__)

app = server.factory_app(debug=True)

# @app.middleware("http")
# async def log_requests(request: Request, call_next):
#     response: Response = await call_next(request)
#     if response.status_code != 200:
#         if isinstance(response, _StreamingResponse):
#             response_body = b""
#             async for chunk in response.body_iterator:
#                 response_body += chunk

#             async def new_body_iterator():
#                 yield response_body

#             response.body_iterator = new_body_iterator()
#             logger.error(f"Response error content: {response_body.decode()}")
#         else:
#             response_body = await response.body()
#             logger.error(f"Response error content: {response_body.decode()}")
#     return response


# @app.exception_handler(Exception)
# async def exception_handler(request: Request, exc: Exception):
#     logger.error(f"An error occurred: {exc}", exc_info=True)
#     return {"detail": "Internal Server Error"}


text_router = text_factory_router()
image_router = image_factory_router()
generic_router = generic_factory_router()
app.include_router(text_router)
app.include_router(image_router)
app.include_router(generic_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=7999)

    # uvicorn miner.server:app --reload --host 127.0.0.1 --port 7999 --env-file .1.env
