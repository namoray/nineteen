from fastapi.routing import APIRouter
from core.tasks_config import TASK_TO_CONFIG
from fiber.logging_utils import get_logger


logger = get_logger(__name__)


async def capacity() -> dict[str, float]:
    return {task: config.max_capacity for task, config in TASK_TO_CONFIG.items()}


def factory_router() -> APIRouter:
    router = APIRouter()
    router.add_api_route("/capacity", capacity, tags=["Subnet"], methods=["GET"])
    return router
