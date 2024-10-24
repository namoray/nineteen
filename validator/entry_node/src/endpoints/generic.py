from typing import Any
from fiber.logging_utils import get_logger
from fastapi.routing import APIRouter
from validator.entry_node.src.models.text_models import llm_models
from core import task_config as tcfg

logger = get_logger(__name__)


async def models() -> list[dict[str, Any]]:
    return tcfg.get_public_task_configs()


router = APIRouter()
router.add_api_route("/v1/models", models, methods=["GET"], tags=["Text"], response_model=None)
