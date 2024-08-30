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

    class Config:
        use_enum_values = True


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
            endpoint=Endpoints.chat_completions.value,
            checking_function="check_text_result",
            task=Task.chat_llama_3_1_8b.value,
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_chat_synthetic", kwargs={"model": Task.chat_llama_3_1_8b.value}
        ),
        endpoint="/chat/completions",
        volume_to_requests_conversion=300,
        is_stream=True,
        weight=0.1,
        timeout=2,
        enabled=True,
    ),
    Task.chat_llama_3_1_70b: FullTaskConfig(
        task=Task.chat_llama_3_1_70b,
        max_capacity=576_000,
        scoring_config=TaskScoringConfig(
            task=Task.chat_llama_3_1_70b, mean=1 / 80, variance=100, overhead=1.0, task_type=TaskType.TEXT
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            server_needed=ServerType.LLM.value,
            load_model_config={
                "model": "casperhansen/llama-3-70b-instruct-awq",
                "half_precision": True,
                "tokenizer": "tau-vision/llama-3-tokenizer-fix",
            },
            endpoint=Endpoints.chat_completions.value,
            checking_function="check_text_result",
            task=Task.chat_llama_3_1_70b.value,
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
            server_needed=ServerType.IMAGE.value,
            load_model_config={},
            checking_function="check_image_result",
            endpoint=Endpoints.text_to_image.value,
            task=Task.proteus_text_to_image.value,
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
            server_needed=ServerType.IMAGE.value,
            load_model_config={},
            checking_function="check_image_result",
            endpoint=Endpoints.text_to_image.value,
            task=Task.proteus_image_to_image.value,
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
            server_needed=ServerType.IMAGE.value,
            load_model_config={},
            checking_function="check_image_result",
            endpoint=Endpoints.text_to_image.value,
            task=Task.dreamshaper_text_to_image.value,
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
            server_needed=ServerType.IMAGE.value,
            load_model_config={},
            checking_function="check_image_result",
            endpoint=Endpoints.text_to_image.value,
            task=Task.dreamshaper_image_to_image.value,
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
            load_model_config={},
            checking_function="check_image_result",
            endpoint=Endpoints.text_to_image.value,
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
            server_needed=ServerType.IMAGE.value,
            load_model_config={},
            checking_function="check_image_result",
            endpoint=Endpoints.text_to_image.value,
            task=Task.flux_schnell_image_to_image.value,
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
            server_needed=ServerType.IMAGE.value,
            load_model_config={},
            checking_function="check_image_result",
            endpoint=Endpoints.text_to_image.value,
            task=Task.avatar.value,
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
            server_needed=ServerType.IMAGE.value,
            load_model_config={},
            checking_function="check_image_result",
            endpoint=Endpoints.text_to_image.value,
            task=Task.inpaint.value,
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
