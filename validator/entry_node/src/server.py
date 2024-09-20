from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from validator.entry_node.src.endpoints.text import router as chat_router
from validator.entry_node.src.endpoints.image import router as image_router
from validator.entry_node.src.endpoints.generic import router as generic_router
from fastapi.middleware.cors import CORSMiddleware
from validator.entry_node.src.core import configuration
from core.logging import get_logger
from scalar_fastapi import get_scalar_api_reference
logger = get_logger(__name__)


def factory_app(debug: bool = False) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await configuration.factory_config()  # Cachin'
        yield

        logger.info("Shutting down...")

    app = FastAPI(lifespan=lifespan, debug=debug)

    
    async def scalar_html():
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,  # type: ignore
            title=app.title,
    )

    app.add_api_route("/scalar", scalar_html, methods=["GET"])

    return app


app = factory_app()
app.include_router(chat_router)
app.include_router(image_router)
app.include_router(generic_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# @app.middleware("http")
# async def log_requests(request: Request, call_next):
#     logger.debug(f"request body: {await request.body()}")
#     response: Response = await call_next(request)
#     if response.status_code != 200:
#         if isinstance(response, _StreamingResponse):
#             response_body = b""
#             async for chunk in response.body_iterator:
#                 response_body += chunk   # type: ignore

#             async def new_body_iterator():
#                 yield response_body

#             response.body_iterator = new_body_iterator()
#             logger.error(f"Response error content: {response_body.decode()}")
#         else:
#             response_body = await response.body()  # type: ignore
#             logger.error(f"Response error content: {response_body.decode()}")
#     return response


# @app.exception_handler(Exception)
# async def exception_handler(request: Request, exc: Exception):
#     logger.error(f"An error occurred: {exc}", exc_info=True)
#     return {"detail": "Internal Server Error"}



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8091)

    # uvicorn validator.entry_node.src.server:app --reload --host 0.0.0.0 --port 8091 --env-file .vali.env
