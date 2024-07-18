from typing import Any, Dict
from core import Task
from . import capacity_operation  # noqa
from . import chat_operation  # noqa
from . import text_to_image_operation  # noqa
from . import image_to_image_operation  # noqa
from . import upscale_operation  # noqa
from . import inpaint_operation  # noqa
from . import clip_embeddings_operation  # noqa
from . import avatar_operation  # noqa


TASKS_TO_MINER_OPERATION_MODULES: Dict[Task, Any] = {
    Task.chat_mixtral: chat_operation,
    Task.chat_llama_3: chat_operation,
    Task.proteus_text_to_image: text_to_image_operation,
    Task.playground_text_to_image: text_to_image_operation,
    Task.dreamshaper_text_to_image: text_to_image_operation,
    Task.proteus_image_to_image: image_to_image_operation,
    Task.playground_image_to_image: image_to_image_operation,
    Task.dreamshaper_image_to_image: image_to_image_operation,
    Task.jugger_inpainting: inpaint_operation,
    Task.avatar: avatar_operation,
    # Task.clip_image_embeddings: clip_embeddings_operation,
}
