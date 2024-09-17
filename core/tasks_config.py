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
            task=Task.chat_llama_3_1_8b, overhead=0.4, mean=0.3, variance=4, task_type=TaskType.TEXT
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            server_needed=ServerType.LLM,
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
        endpoint=Endpoints.chat_completions.value,
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
            task=Task.chat_llama_3_1_70b, overhead=0.3, mean=0.018, variance=130, task_type=TaskType.TEXT
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            server_needed=ServerType.LLM,
            load_model_config={
                "model": "hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4",
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
        endpoint=Endpoints.chat_completions.value,
        volume_to_requests_conversion=300,
        is_stream=True,
        weight=0.1,
        timeout=2,
        enabled=True,
    ),
    Task.proteus_text_to_image: FullTaskConfig(
        task=Task.proteus_text_to_image,
        max_capacity=3_600,
        scoring_config=TaskScoringConfig(
            task=Task.proteus_text_to_image, mean=0.2, variance=7, overhead=0.25, task_type=TaskType.IMAGE
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            server_needed=ServerType.IMAGE,
            load_model_config={},
            checking_function="check_image_result",
            endpoint=Endpoints.text_to_image.value,
            task=Task.proteus_text_to_image.value,
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_text_to_image_synthetic",
            kwargs={"model": Task.proteus_text_to_image.value},
        ),
        endpoint=Endpoints.text_to_image.value,
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
            task=Task.proteus_image_to_image, mean=0.24, variance=5, overhead=0.6, task_type=TaskType.IMAGE
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            server_needed=ServerType.IMAGE,
            load_model_config={},
            checking_function="check_image_result",
            endpoint=Endpoints.image_to_image.value,
            task=Task.proteus_image_to_image.value,
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_image_to_image_synthetic",
            kwargs={"model": Task.proteus_image_to_image.value},
        ),
        endpoint=Endpoints.image_to_image.value,
        volume_to_requests_conversion=10,
        is_stream=False,
        weight=0.1,
        timeout=20,
        enabled=False,
    ),
    Task.flux_schnell_text_to_image: FullTaskConfig(
        task=Task.flux_schnell_text_to_image,
        max_capacity=3_600,
        scoring_config=TaskScoringConfig(
            task=Task.flux_schnell_text_to_image, mean=0.30, variance=7, overhead=0.4, task_type=TaskType.IMAGE
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            server_needed=ServerType.IMAGE,
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
        enabled=True,
    ),
    Task.flux_schnell_image_to_image: FullTaskConfig(
        task=Task.flux_schnell_image_to_image,
        max_capacity=2_000,
        scoring_config=TaskScoringConfig(
            task=Task.flux_schnell_image_to_image, mean=0.36, variance=5, overhead=0.6, task_type=TaskType.IMAGE
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            server_needed=ServerType.IMAGE,
            load_model_config={},
            checking_function="check_image_result",
            endpoint=Endpoints.image_to_image.value,
            task=Task.flux_schnell_image_to_image.value,
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_image_to_image_synthetic",
            kwargs={"model": Task.flux_schnell_image_to_image.value},
        ),
        endpoint=Endpoints.image_to_image.value,
        volume_to_requests_conversion=10,
        is_stream=False,
        weight=0.1,
        timeout=15,
        enabled=False,
    ),
    Task.avatar: FullTaskConfig(
        task=Task.avatar,
        max_capacity=2_000,
        scoring_config=TaskScoringConfig(task=Task.avatar, mean=0.50, variance=4, overhead=0.5, task_type=TaskType.IMAGE),
        orchestrator_server_config=OrchestratorServerConfig(
            server_needed=ServerType.IMAGE,
            load_model_config={},
            checking_function="check_image_result",
            endpoint=Endpoints.avatar.value,
            task=Task.avatar.value,
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_avatar_synthetic",
            kwargs={},
        ),
        endpoint=Endpoints.avatar.value,
        volume_to_requests_conversion=10,
        is_stream=False,
        weight=0.1,
        timeout=15,
        enabled=False,
    ),
    Task.dreamshaper_text_to_image: FullTaskConfig(
        task=Task.dreamshaper_text_to_image,
        max_capacity=3_600,
        scoring_config=TaskScoringConfig(
            task=Task.dreamshaper_text_to_image, mean=0.22, variance=7, overhead=0.3, task_type=TaskType.IMAGE
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            server_needed=ServerType.IMAGE,
            load_model_config={},
            checking_function="check_image_result",
            endpoint=Endpoints.text_to_image.value,
            task=Task.dreamshaper_text_to_image.value,
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_text_to_image_synthetic",
            kwargs={"model": Task.dreamshaper_text_to_image.value},
        ),
        endpoint=Endpoints.text_to_image.value,
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
            task=Task.dreamshaper_image_to_image, mean=0.28, variance=5, overhead=0.6, task_type=TaskType.IMAGE
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            server_needed=ServerType.IMAGE,
            load_model_config={},
            checking_function="check_image_result",
            endpoint=Endpoints.image_to_image.value,
            task=Task.dreamshaper_image_to_image.value,
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_image_to_image_synthetic",
            kwargs={"model": Task.dreamshaper_image_to_image.value},
        ),
        endpoint=Endpoints.image_to_image.value,
        volume_to_requests_conversion=10,
        is_stream=False,
        weight=0.1,
        timeout=15,
        enabled=False,
    ),
    Task.inpaint: FullTaskConfig(
        task=Task.inpaint,
        max_capacity=2_000,
        scoring_config=TaskScoringConfig(
            task=Task.inpaint, mean=0.3, variance=4, overhead=0.4, task_type=TaskType.IMAGE
        ),
        orchestrator_server_config=OrchestratorServerConfig(
            server_needed=ServerType.IMAGE,
            load_model_config={},
            checking_function="check_image_result",
            endpoint=Endpoints.inpaint.value,
            task=Task.inpaint.value,
        ),
        synthetic_generation_config=SyntheticGenerationConfig(
            func="generate_inpaint_synthetic",
            kwargs={"model": Task.inpaint.value},
        ),
        endpoint=Endpoints.inpaint.value,
        volume_to_requests_conversion=10,
        is_stream=False,
        weight=0.1,
        timeout=15,
        enabled=False,
    ),
}


def get_enabled_task_config(task: Task | str) -> FullTaskConfig | None:
    if isinstance(task, str):
        try:
            task = Task(task)
        except ValueError:
            return None
    config = TASK_TO_CONFIG.get(task)
    if config is None or not config.enabled:
        return None
    return config
