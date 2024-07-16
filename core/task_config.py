
from core import Task
from models.base_models import VolumeForTask

TASK_TO_MAX_CAPACITY: dict[Task, VolumeForTask] = {
    Task.chat_mixtral: VolumeForTask(volume=576_000),
    Task.chat_llama_3: VolumeForTask(volume=576_000),
    Task.proteus_text_to_image: VolumeForTask(volume=3_600),
    Task.playground_text_to_image: VolumeForTask(volume=10_000),
    Task.dreamshaper_text_to_image: VolumeForTask(volume=3_000),
    Task.proteus_image_to_image: VolumeForTask(volume=3_600),
    Task.playground_image_to_image: VolumeForTask(volume=10_000),
    Task.dreamshaper_image_to_image: VolumeForTask(volume=3_000),
    Task.jugger_inpainting: VolumeForTask(volume=4_000),
    Task.clip_image_embeddings: VolumeForTask(volume=0),  # disabled clip for now
    Task.avatar: VolumeForTask(volume=1_120),
}
