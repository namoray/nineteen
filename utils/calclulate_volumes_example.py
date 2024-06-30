"""
Use this code to calculate a volume estimation for each task
If you prefer, you can remove the 'mean' estimation and instead insert your own estimation of speed per step or token
So you can more accurately calculate your own volume
"""

from core import Task, tasks
from core import constants as core_cst
from validation.proxy.work_and_speed_functions import TaskType


def calculate_volume_for_task(
    task: Task, concurrent_requests_each_gpu_server_can_handle: float, gpus_with_server_on: float = 1
) -> int:
    vol_in_seconds = gpus_with_server_on * concurrent_requests_each_gpu_server_can_handle * core_cst.SCORING_PERIOD_TIME

    task_config = tasks.get_task_config(task)

    # You can change this if you have better/worse hardware
    mean = task_config.mean

    # In the case of llm, this will get the number of characters we can do
    if task_config.task_type == TaskType.TEXT:
        vol_in_chars = vol_in_seconds / mean
        vol_in_tokens = vol_in_chars / 4
        vol = vol_in_tokens
    elif task_config.task_type == TaskType.IMAGE:
        vol_in_steps = vol_in_seconds / mean
        vol = vol_in_steps
    elif task_config.task_type == TaskType.CLIP:
        vol_in_images = vol_in_seconds / mean
        vol = vol_in_images

    ## If we were to have average speed, we would have a volume in

    return int(vol)


# Here are some examples
calculate_volume_for_task(Task.chat_llama_3, concurrent_requests_each_gpu_server_can_handle=20, gpus_with_server_on=1)

calculate_volume_for_task(Task.chat_llama_3, concurrent_requests_each_gpu_server_can_handle=20, gpus_with_server_on=1)
calculate_volume_for_task(Task.chat_mixtral, concurrent_requests_each_gpu_server_can_handle=10, gpus_with_server_on=1)

calculate_volume_for_task(
    Task.playground_text_to_image, concurrent_requests_each_gpu_server_can_handle=1, gpus_with_server_on=1
)
calculate_volume_for_task(
    Task.proteus_text_to_image, concurrent_requests_each_gpu_server_can_handle=1, gpus_with_server_on=1
)
