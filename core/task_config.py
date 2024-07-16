
from core import Task
from models.base_models import CapacityForTask

TASK_TO_MAX_CAPACITY: dict[Task, CapacityForTask] = {
    Task.chat_mixtral: CapacityForTask(capacity=576_000),
    Task.chat_llama_3: CapacityForTask(capacity=576_000),
    Task.proteus_text_to_image: CapacityForTask(capacity=3_600),
    Task.playground_text_to_image: CapacityForTask(capacity=10_000),
    Task.dreamshaper_text_to_image: CapacityForTask(capacity=3_000),
    Task.proteus_image_to_image: CapacityForTask(capacity=3_600),
    Task.playground_image_to_image: CapacityForTask(capacity=10_000),
    Task.dreamshaper_image_to_image: CapacityForTask(capacity=3_000),
    Task.jugger_inpainting: CapacityForTask(capacity=4_000),
    Task.clip_image_embeddings: CapacityForTask(capacity=0),  # disabled clip for now
    Task.avatar: CapacityForTask(capacity=1_120),
}
