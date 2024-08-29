from enum import Enum
from pydantic import BaseModel, Field
from core.tasks import Task


class TaskType(Enum):
    IMAGE = "image"
    TEXT = "text"
    CLIP = "clip"


class ServerType(Enum):
    LLM = "llm_server"
    IMAGE = "image_server"


class Endpoints(Enum):
    text_to_image = "/text-to-image"
    image_to_image = "/image-to-image"
    avatar = "/avatar"
    inpaint = "/inpaint"
    upscale = "/upscale"
    clip_embeddings = "/clip-embeddings"
    chat_completions = "/chat/completions"


class TaskScoringConfig(BaseModel):
    task: Task
    mean: float
    variance: float
    overhead: float
    task_type: TaskType


class OrchestratorServerConfig(BaseModel):
    server_needed: ServerType = Field(examples=[ServerType.LLM, ServerType.IMAGE])
    load_model_config: dict | None = Field(examples=[None])
    checking_function: str = Field(examples=["check_text_result", "check_image_result"])
    task: str = Field(examples=["chat-llama-3-1-8b"])
    endpoint: str = Field(examples=["/generate_text"])


class SyntheticGenerationConfig(BaseModel):
    func: str
    kwargs: dict


class FullTaskConfig(BaseModel):
    task: Task
    max_capacity: float
    scoring_config: TaskScoringConfig
    orchestrator_server_config: OrchestratorServerConfig
    synthetic_generation_config: SyntheticGenerationConfig
    endpoint: str
    volume_to_requests_conversion: float
    is_stream: bool
    weight: float
    timeout: float
    enabled: bool = True


TASK_TO_CONFIG: dict[Task, FullTaskConfig] = {
    Task.chat_llama_3_1_8b: FullTaskConfig(
        task=Task.chat_llama_3_1_8b,
        max_capacity=576_000,
        scoring_config=TaskScoringConfig(
            task=Task.chat_llama_3_1_8b, mean=1 / 80, variance=100, overhead=1.0, task_type=TaskType.TEXT
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            server_needed=ServerType.LLM.value,
            load_model_config={
                "model": "unsloth/Meta-Llama-3.1-8B-Instruct",
                "half_precision": True,
                "tokenizer": "tau-vision/llama-tokenizer-fix",
                "max_model_len": 16000,
                "gpu_utilization": 0.6,
            },
            endpoint=Endpoints.text_to_image.value,
            checking_function="check_text_result",
            task=Task.flux_schnell_text_to_image.value,
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_chat_synthetic", kwargs={"model": Task.chat_llama_3_1_8b.value}
        ),
        endpoint="/chat/completions",
        volume_to_requests_conversion=300,
        is_stream=True,
        weight=0.1,
        timeout=2,
        enabled=False,
    ),
    Task.chat_llama_3_1_70b: FullTaskConfig(
        task=Task.chat_llama_3_1_70b,
        max_capacity=576_000,
        scoring_config=TaskScoringConfig(
            task=Task.chat_llama_3_1_70b, mean=1 / 80, variance=100, overhead=1.0, task_type=TaskType.TEXT
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            checking_server_needed=ServerType.LLM,
            checking_load_model_config={
                "model": "casperhansen/llama-3-70b-instruct-awq",
                "half_precision": True,
                "tokenizer": "tau-vision/llama-3-tokenizer-fix",
            },
            checking_function="check_text_result",
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_chat_synthetic", kwargs={"model": Task.chat_llama_3_1_70b.value}
        ),
        endpoint="/chat/completions",
        volume_to_requests_conversion=300,
        is_stream=True,
        weight=0.1,
        timeout=2,
        enabled=False,
    ),
    Task.proteus_text_to_image: FullTaskConfig(
        task=Task.proteus_text_to_image,
        max_capacity=3_600,
        scoring_config=TaskScoringConfig(
            task=Task.proteus_text_to_image, mean=0.32, variance=3, overhead=0.5, task_type=TaskType.IMAGE
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            checking_server_needed=ServerType.IMAGE,
            checking_load_model_config={},
            checking_function="check_image_result",
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_text_to_image_synthetic",
            kwargs={"model": Task.proteus_text_to_image.value},
        ),
        endpoint="/text-to-image",
        volume_to_requests_conversion=10,
        is_stream=False,
        weight=0.1,
        timeout=5,
        enabled=False,
    ),
    Task.proteus_image_to_image: FullTaskConfig(
        task=Task.proteus_image_to_image,
        max_capacity=2_000,
        scoring_config=TaskScoringConfig(
            task=Task.proteus_image_to_image, mean=0.35, variance=3, overhead=0.5, task_type=TaskType.IMAGE
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            checking_server_needed=ServerType.IMAGE,
            checking_load_model_config={},
            checking_function="check_image_result",
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_image_to_image_synthetic",
            kwargs={"model": Task.proteus_image_to_image.value},
        ),
        endpoint="/image-to-image",
        volume_to_requests_conversion=10,
        is_stream=False,
        weight=0.1,
        timeout=20,
        enabled=False,
    ),
    Task.dreamshaper_text_to_image: FullTaskConfig(
        task=Task.dreamshaper_text_to_image,
        max_capacity=3_600,
        scoring_config=TaskScoringConfig(
            task=Task.dreamshaper_text_to_image, mean=0.40, variance=3, overhead=0.5, task_type=TaskType.IMAGE
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            checking_server_needed=ServerType.IMAGE,
            checking_load_model_config={},
            checking_function="check_image_result",
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_text_to_image_synthetic",
            kwargs={"model": Task.dreamshaper_text_to_image.value},
        ),
        endpoint="/text-to-image",
        volume_to_requests_conversion=10,
        is_stream=False,
        weight=0.1,
        timeout=5,
        enabled=False,
    ),
    Task.dreamshaper_image_to_image: FullTaskConfig(
        task=Task.dreamshaper_image_to_image,
        max_capacity=2_000,
        scoring_config=TaskScoringConfig(
            task=Task.dreamshaper_image_to_image, mean=0.21, variance=5, overhead=0.5, task_type=TaskType.IMAGE
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            checking_server_needed=ServerType.IMAGE,
            checking_load_model_config={},
            checking_function="check_image_result",
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_image_to_image_synthetic",
            kwargs={"model": Task.dreamshaper_image_to_image.value},
        ),
        endpoint="/image-to-image",
        volume_to_requests_conversion=10,
        is_stream=False,
        weight=0.1,
        timeout=15,
        enabled=False,
    ),
    Task.flux_schnell_text_to_image: FullTaskConfig(
        task=Task.flux_schnell_text_to_image,
        max_capacity=3_600,
        scoring_config=TaskScoringConfig(
            task=Task.flux_schnell_text_to_image, mean=0.40, variance=3, overhead=0.5, task_type=TaskType.IMAGE
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            server_needed=ServerType.IMAGE.value,
            load_model_config=None,
            endpoint=Endpoints.text_to_image.value,
            checking_function="check_image_result",
            task=Task.flux_schnell_text_to_image.value,
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_text_to_image_synthetic",
            kwargs={"model": Task.flux_schnell_text_to_image.value},
        ),
        endpoint=Endpoints.text_to_image.value,
        volume_to_requests_conversion=10,
        is_stream=False,
        weight=0.1,
        timeout=20,
        enabled=False,
    ),
    Task.flux_schnell_image_to_image: FullTaskConfig(
        task=Task.flux_schnell_image_to_image,
        max_capacity=2_000,
        scoring_config=TaskScoringConfig(
            task=Task.flux_schnell_image_to_image, mean=0.21, variance=5, overhead=0.5, task_type=TaskType.IMAGE
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            checking_server_needed=ServerType.IMAGE,
            checking_load_model_config={},
            checking_function="check_image_result",
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_image_to_image_synthetic",
            kwargs={"model": Task.flux_schnell_image_to_image.value},
        ),
        endpoint="/image-to-image",
        volume_to_requests_conversion=10,
        is_stream=False,
        weight=0.1,
        timeout=15,
        enabled=False,
    ),
    Task.avatar: FullTaskConfig(
        task=Task.avatar,
        max_capacity=2_000,
        scoring_config=TaskScoringConfig(task=Task.avatar, mean=0.21, variance=5, overhead=0.5, task_type=TaskType.IMAGE),
        orchestrator_server_config=OrchestratorServerConfig(
            checking_server_needed=ServerType.IMAGE,
            checking_load_model_config={},
            checking_function="check_image_result",
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_avatar_synthetic",
            kwargs={},
        ),
        endpoint="/avatar",
        volume_to_requests_conversion=10,
        is_stream=False,
        weight=0.1,
        timeout=15,
        enabled=False,
    ),
    Task.inpaint: FullTaskConfig(
        task=Task.inpaint,
        max_capacity=1,
        scoring_config=TaskScoringConfig(task=Task.inpaint, mean=0.21, variance=5, overhead=0.5, task_type=TaskType.IMAGE),
        orchestrator_server_config=OrchestratorServerConfig(
            checking_server_needed=ServerType.IMAGE,
            checking_load_model_config={},
            checking_function="check_image_result",
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_inpaint_synthetic",
            kwargs={},
        ),
        endpoint="/inpaint",
        volume_to_requests_conversion=10,
        is_stream=False,
        weight=0.1,
        timeout=15,
        enabled=False,
    ),
}


def get_enabled_task_config(task: Task) -> FullTaskConfig | None:
    config = TASK_TO_CONFIG.get(task)
    if config is None or not config.enabled:
        return None
    return config


# task_configs = models.TaskConfigMapping(
#     tasks={
#         models.Task.chat_mixtral.value: models.TaskConfig(
#             server_needed=models.ServerType.LLM,
#             load_model_config=models.ModelConfigDetails(
#                 model="TheBloke/Nous-Hermes-2-Mixtral-8x7B-DPO-GPTQ",
#                 half_precision=True,
#                 revision="gptq-8bit-128g-actorder_True",
#                 gpu_memory_utilization=0.85,
#                 max_model_len=8000,
#             ),
#             endpoint=BASE_URL + "/generate_text",
#             checking_function=text_based.check_text_result,
#             task=models.Task.chat_mixtral,
#         ),
#         models.Task.chat_llama_3.value: models.TaskConfig(
#             server_needed=models.ServerType.LLM,
#             load_model_config=models.ModelConfigDetails(
#                 model="casperhansen/llama-3-70b-instruct-awq",
#                 tokenizer="tau-vision/llama-3-tokenizer-fix",
#                 half_precision=True,
#                 gpu_memory_utilization=0.85,
#                 max_model_len=8000,
#             ),
#             endpoint=BASE_URL + "/generate_text",
#             checking_function=text_based.check_text_result,
#             task=models.Task.chat_llama_3,
#         ),
#         models.Task.chat_llama_31_8b.value: models.TaskConfig(
#             server_needed=models.ServerType.LLM,
#             load_model_config=models.ModelConfigDetails(
#                 model="unsloth/Meta-Llama-3.1-8B-Instruct",
#                 tokenizer="tau-vision/llama-tokenizer-fix",
#                 half_precision=True,
#                 gpu_memory_utilization=0.85,
#                 max_model_len=16000,
#             ),
#             endpoint=BASE_URL + "/generate_text",
#             checking_function=text_based.check_text_result,
#             task=models.Task.chat_llama_31_8b,
#         ),
#         models.Task.chat_llama_31_70b.value: models.TaskConfig(
#             server_needed=models.ServerType.LLM,
#             load_model_config=models.ModelConfigDetails(
#                 model="hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4",
#                 tokenizer="tau-vision/llama-tokenizer-fix",
#                 half_precision=True,
#                 gpu_memory_utilization=0.85,
#                 max_model_len=16000,
#             ),
#             endpoint=BASE_URL + "/generate_text",
#             checking_function=text_based.check_text_result,
#             task=models.Task.chat_llama_31_70b,
#         ),
#         models.Task.proteus_text_to_image.value: models.TaskConfig(
#             server_needed=models.ServerType.IMAGE,
#             load_model_config=None,
#             endpoint=BASE_URL + Endpoints.text_to_image.value,
#             checking_function=image_based.check_image_result,
#             task=models.Task.proteus_text_to_image,
#         ),

#         models.Task.playground_text_to_image.value: models.TaskConfig(
#             server_needed=models.ServerType.IMAGE,
#             load_model_config=None,
#             endpoint=BASE_URL + Endpoints.text_to_image.value,
#             checking_function=image_based.check_image_result,
#             task=models.Task.playground_text_to_image,
#         ),
#         models.Task.playground_text_to_image.value: models.TaskConfig(
#             server_needed=models.ServerType.IMAGE,
#             load_model_config=None,
#             endpoint=BASE_URL + Endpoints.text_to_image.value,
#             checking_function=image_based.check_image_result,
#             task=models.Task.playground_text_to_image,
#         ),
#         models.Task.dreamshaper_text_to_image.value: models.TaskConfig(
#             server_needed=models.ServerType.IMAGE,
#             load_model_config=None,
#             endpoint=BASE_URL + Endpoints.text_to_image.value,
#             checking_function=image_based.check_image_result,
#             task=models.Task.dreamshaper_text_to_image,
#         ),
#         models.Task.proteus_image_to_image.value: models.TaskConfig(
#             server_needed=models.ServerType.IMAGE,
#             load_model_config=None,
#             endpoint=BASE_URL + Endpoints.image_to_image.value,
#             checking_function=image_based.check_image_result,
#             task=models.Task.proteus_image_to_image,
#         ),
#         models.Task.playground_image_to_image.value: models.TaskConfig(
#             server_needed=models.ServerType.IMAGE,
#             load_model_config=None,
#             endpoint=BASE_URL + Endpoints.image_to_image.value,
#             checking_function=image_based.check_image_result,
#             task=models.Task.playground_image_to_image,
#         ),
#         models.Task.flux_schnell_image_to_image.value: models.TaskConfig(
#             server_needed=models.ServerType.IMAGE,
#             load_model_config=None,
#             endpoint=BASE_URL + Endpoints.image_to_image.value,
#             checking_function=image_based.check_image_result,
#             task=models.Task.flux_schnell_image_to_image,
#         ),
#         models.Task.dreamshaper_image_to_image.value: models.TaskConfig(
#             server_needed=models.ServerType.IMAGE,
#             load_model_config=None,
#             endpoint=BASE_URL + Endpoints.image_to_image.value,
#             checking_function=image_based.check_image_result,
#             task=models.Task.dreamshaper_image_to_image,
#         ),
#         models.Task.avatar.value: models.TaskConfig(
#             server_needed=models.ServerType.IMAGE,
#             load_model_config=None,
#             endpoint=BASE_URL + Endpoints.avatar.value,
#             checking_function=image_based.check_image_result,
#             task=models.Task.avatar,
#         ),
#         models.Task.jugger_inpainting.value: models.TaskConfig(
#             server_needed=models.ServerType.IMAGE,
#             load_model_config=None,
#             endpoint=BASE_URL + Endpoints.inpaint.value,
#             checking_function=image_based.check_image_result,
#             task=models.Task.jugger_inpainting,
#         ),
#     }
# )
