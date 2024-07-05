"""Would prefer to make this just one dataclass"""

from enum import Enum
from pydantic import BaseModel
from core import Task
from models import synapses, utility_models
from typing import Dict, Optional
import bittensor as bt

# I don't love this being here. How else should I do it though?
# I don't want to rely on any extra third party service for fetching this info...


TASK_IS_STREAM: Dict[Task, bool] = {
    Task.chat_mixtral: True,
    Task.chat_llama_3: True,
    Task.proteus_text_to_image: False,
    Task.playground_text_to_image: False,
    Task.dreamshaper_text_to_image: False,
    Task.proteus_image_to_image: False,
    Task.playground_image_to_image: False,
    Task.dreamshaper_image_to_image: False,
    Task.jugger_inpainting: False,
    Task.clip_image_embeddings: False,
    Task.avatar: False,
}
TASKS_TO_SYNAPSE: Dict[Task, bt.Synapse] = {
    Task.chat_mixtral: synapses.Chat,
    Task.chat_llama_3: synapses.Chat,
    Task.proteus_text_to_image: synapses.TextToImage,
    Task.playground_text_to_image: synapses.TextToImage,
    Task.dreamshaper_text_to_image: synapses.TextToImage,
    Task.proteus_image_to_image: synapses.ImageToImage,
    Task.playground_image_to_image: synapses.ImageToImage,
    Task.dreamshaper_image_to_image: synapses.ImageToImage,
    Task.jugger_inpainting: synapses.Inpaint,
    Task.clip_image_embeddings: synapses.ClipEmbeddings,
    Task.avatar: synapses.Avatar,
}


def get_task_from_synapse(synapse: bt.Synapse) -> Optional[Task]:
    if isinstance(synapse, synapses.Chat):
        if synapse.model == utility_models.ChatModels.mixtral.value:
            return Task.chat_mixtral
        elif synapse.model == utility_models.ChatModels.llama_3.value:
            return Task.chat_llama_3
        else:
            return None
    elif isinstance(synapse, synapses.TextToImage):
        if synapse.engine == utility_models.EngineEnum.PROTEUS.value:
            return Task.proteus_text_to_image
        elif synapse.engine == utility_models.EngineEnum.PLAYGROUND.value:
            return Task.playground_text_to_image
        elif synapse.engine == utility_models.EngineEnum.DREAMSHAPER.value:
            return Task.dreamshaper_text_to_image
        else:
            return None
    elif isinstance(synapse, synapses.ImageToImage):
        if synapse.engine == utility_models.EngineEnum.PROTEUS.value:
            return Task.proteus_image_to_image
        elif synapse.engine == utility_models.EngineEnum.PLAYGROUND.value:
            return Task.playground_image_to_image
        elif synapse.engine == utility_models.EngineEnum.DREAMSHAPER.value:
            return Task.dreamshaper_image_to_image
        else:
            return None
    elif isinstance(synapse, synapses.Inpaint):
        return Task.jugger_inpainting
    elif isinstance(synapse, synapses.ClipEmbeddings):
        return Task.clip_image_embeddings
    elif isinstance(synapse, synapses.Avatar):
        return Task.avatar
    else:
        return None


class TaskType(Enum):
    IMAGE = "image"
    TEXT = "text"
    CLIP = "clip"


class TaskConfig(BaseModel):
    task: Task
    overhead: float
    mean: float
    variance: float
    task_type: TaskType


TASK_CONFIGS = [
    TaskConfig(
        task=Task.proteus_text_to_image,
        overhead=0.5,
        mean=0.32,
        variance=3,
        task_type=TaskType.IMAGE,
    ),
    TaskConfig(
        task=Task.dreamshaper_text_to_image,
        overhead=0.5,
        mean=0.40,
        variance=3,
        task_type=TaskType.IMAGE,
    ),
    TaskConfig(
        task=Task.playground_text_to_image,
        overhead=0.5,
        mean=0.18,
        variance=3,
        task_type=TaskType.IMAGE,
    ),
    TaskConfig(
        task=Task.proteus_image_to_image,
        overhead=0.5,
        mean=0.35,
        variance=3,
        task_type=TaskType.IMAGE,
    ),
    TaskConfig(
        task=Task.dreamshaper_image_to_image,
        overhead=0.5,
        mean=0.40,
        variance=3,
        task_type=TaskType.IMAGE,
    ),
    TaskConfig(
        task=Task.playground_image_to_image,
        overhead=0.5,
        mean=0.21,
        variance=5,
        task_type=TaskType.IMAGE,
    ),
    TaskConfig(
        task=Task.jugger_inpainting,
        overhead=1.2,
        mean=0.23,
        variance=2,
        task_type=TaskType.IMAGE,
    ),
    TaskConfig(task=Task.avatar, overhead=5, mean=1, variance=20, task_type=TaskType.IMAGE),
    TaskConfig(
        task=Task.chat_mixtral,
        overhead=1,
        mean=1 / 80,
        variance=100,
        task_type=TaskType.TEXT,
    ),
    TaskConfig(
        task=Task.chat_llama_3,
        overhead=1,
        mean=1 / 80,
        variance=100,
        task_type=TaskType.TEXT,
    ),
    TaskConfig(
        task=Task.clip_image_embeddings,
        overhead=1,
        mean=0.5,
        variance=2,
        task_type=TaskType.CLIP,
    ),
]


def get_task_config(task: Task) -> TaskConfig:
    for config in TASK_CONFIGS:
        if config.task == task:
            return config
    raise ValueError(f"Task configuration for {task.value} not found")


# LLM VOLUMES ARE IN TOKENS,
# IMAGE VOLUMES ARE IN STEP
# CLIP IS IN IMAGES
TASK_TO_VOLUME_TO_REQUESTS_CONVERSION: Dict[Task, float] = {
    Task.chat_llama_3: 300,
    Task.chat_mixtral: 300,
    Task.proteus_text_to_image: 10,
    Task.playground_text_to_image: 50,
    Task.dreamshaper_text_to_image: 10,
    Task.proteus_image_to_image: 10,
    Task.playground_image_to_image: 50,
    Task.dreamshaper_image_to_image: 10,
    Task.jugger_inpainting: 20,
    Task.avatar: 10,
    Task.clip_image_embeddings: 1,
}