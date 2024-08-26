from enum import Enum
from pydantic import BaseModel
from core.tasks import Task


class TaskType(Enum):
    IMAGE = "image"
    TEXT = "text"
    CLIP = "clip"


class ServerType(Enum):
    LLM = "llm_server"
    IMAGE = "image_server"


class TaskScoringConfig(BaseModel):
    task: Task
    mean: float
    variance: float
    overhead: float
    task_type: TaskType


class OrchestratorServerConfig(BaseModel):
    checking_server_needed: ServerType
    checking_load_model_config: dict
    checking_function: str


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


TASK_TO_CONFIG: dict[Task, FullTaskConfig] = {
    # Task.chat_llama_3_1_8b: FullTaskConfig(
    #     task=Task.chat_llama_3_1_8b,
    #     max_capacity=576_000,
    #     scoring_config=TaskScoringConfig(
    #         task=Task.chat_llama_3_1_8b, mean=1 / 80, variance=100, overhead=1.0, task_type=TaskType.TEXT
    #     ),
    #     orchestrator_server_config=OrchestratorServerConfig(
    #         checking_server_needed=ServerType.LLM,
    #         checking_load_model_config={
    #             "model": "TheBloke/Nous-Hermes-2-Mixtral-8x7B-DPO-GPTQ",
    #             "half_precision": True,
    #             "revision": "gptq-8bit-128g-actorder_True",
    #         },
    #         checking_function="check_text_result",
    #     ),
    #     synthetic_generation_config=SyntheticGenerationConfig(
    #         func="generate_chat_synthetic", kwargs={"model": Task.chat_llama_3_1_8b.value}
    #     ),
    #     endpoint="/chat/completions",
    #     volume_to_requests_conversion=300,
    #     is_stream=True,
    #     weight=0.1,
    #     timeout=2,
    # ),
    # Task.chat_llama_3_1_70b: FullTaskConfig(
    #     task=Task.chat_llama_3_1_70b,
    #     max_capacity=576_000,
    #     scoring_config=TaskScoringConfig(
    #         task=Task.chat_llama_3_1_70b, mean=1 / 80, variance=100, overhead=1.0, task_type=TaskType.TEXT
    #     ),
    #     orchestrator_server_config=OrchestratorServerConfig(
    #         checking_server_needed=ServerType.LLM,
    #         checking_load_model_config={
    #             "model": "casperhansen/llama-3-70b-instruct-awq",
    #             "half_precision": True,
    #             "tokenizer": "tau-vision/llama-3-tokenizer-fix",
    #         },
    #         checking_function="check_text_result",
    #     ),
    #     synthetic_generation_config=SyntheticGenerationConfig(
    #         func="generate_chat_synthetic", kwargs={"model": Task.chat_llama_3_1_70b.value}
    #     ),
    #     endpoint="/chat/completions",
    #     volume_to_requests_conversion=300,
    #     is_stream=True,
    #     weight=0.1,
    #     timeout=2,
    # ),
    # Task.proteus_text_to_image: FullTaskConfig(
    #     task=Task.proteus_text_to_image,
    #     max_capacity=3_600,
    #     scoring_config=TaskScoringConfig(
    #         task=Task.proteus_text_to_image, mean=0.32, variance=3, overhead=0.5, task_type=TaskType.IMAGE
    #     ),
    #     orchestrator_server_config=OrchestratorServerConfig(
    #         checking_server_needed=ServerType.IMAGE,
    #         checking_load_model_config={},
    #         checking_function="check_image_result",
    #     ),
    #     synthetic_generation_config=SyntheticGenerationConfig(
    #         func="generate_text_to_image_synthetic",
    #         kwargs={"model": Task.proteus_text_to_image.value},
    #     ),
    #     endpoint="/text-to-image",
    #     volume_to_requests_conversion=10,
    #     is_stream=False,
    #     weight=0.1,
    #     timeout=5,
    # ),
    # Task.dreamshaper_text_to_image: FullTaskConfig(
    #     task=Task.dreamshaper_text_to_image,
    #     max_capacity=3_600,
    #     scoring_config=TaskScoringConfig(
    #         task=Task.dreamshaper_text_to_image, mean=0.40, variance=3, overhead=0.5, task_type=TaskType.IMAGE
    #     ),
    #     orchestrator_server_config=OrchestratorServerConfig(
    #         checking_server_needed=ServerType.IMAGE,
    #         checking_load_model_config={},
    #         checking_function="check_image_result",
    #     ),
    #     synthetic_generation_config=SyntheticGenerationConfig(
    #         func="generate_text_to_image_synthetic",
    #         kwargs={"model": Task.dreamshaper_text_to_image.value},
    #     ),
    #     endpoint="/text-to-image",
    #     volume_to_requests_conversion=10,
    #     is_stream=False,
    #     weight=0.1,
    #     timeout=5,
    # ),
    # Task.flux_schnell_text_to_image: FullTaskConfig(
    #     task=Task.flux_schnell_text_to_image,
    #     max_capacity=3_600,
    #     scoring_config=TaskScoringConfig(
    #         task=Task.flux_schnell_text_to_image, mean=0.40, variance=3, overhead=0.5, task_type=TaskType.IMAGE
    #     ),
    #     orchestrator_server_config=OrchestratorServerConfig(
    #         checking_server_needed=ServerType.IMAGE,
    #         checking_load_model_config={},
    #         checking_function="check_image_result",
    #     ),
    #     synthetic_generation_config=SyntheticGenerationConfig(
    #         func="generate_text_to_image_synthetic",
    #         kwargs={"model": Task.flux_schnell_text_to_image.value},
    #     ),
    #     endpoint="/text-to-image",
    #     volume_to_requests_conversion=10,
    #     is_stream=False,
    #     weight=0.1,
    #     timeout=20,
    # ),
    # Task.proteus_image_to_image: FullTaskConfig(
    #     task=Task.proteus_image_to_image,
    #     max_capacity=float(capacity=3_600,
    #     scoring_config=TaskScoringConfig(
    #         task=Task.proteus_image_to_image, mean=0.35, variance=3, overhead=0.5, task_type=TaskType.IMAGE
    #     ),
    #     orchestrator_server_config=OrchestratorServerConfig(
    #         checking_server_needed=ServerType.IMAGE,
    #         checking_load_model_config={},
    #         checking_function="check_image_result",
    #     ),
    #     synthetic_generation_config=SyntheticGenerationConfig(
    #         func="generate_image_to_image_synthetic",
    #         kwargs={"engine": "proteus"},
    #     ),
    #     endpoint="ImageToImage",
    #     volume_to_requests_conversion=10,
    #     is_stream=False,
    # ),
    # Task.flux_schnell_image_to_image: FullTaskConfig(
    #     task=Task.flux_schnell_image_to_image,
    #     max_capacity=2_000,
    #     scoring_config=TaskScoringConfig(
    #         task=Task.flux_schnell_image_to_image, mean=0.21, variance=5, overhead=0.5, task_type=TaskType.IMAGE
    #     ),
    #     orchestrator_server_config=OrchestratorServerConfig(
    #         checking_server_needed=ServerType.IMAGE,
    #         checking_load_model_config={},
    #         checking_function="check_image_result",
    #     ),
    #     synthetic_generation_config=SyntheticGenerationConfig(
    #         func="generate_image_to_image_synthetic",
    #         kwargs={"model": Task.flux_schnell_image_to_image.value},
    #     ),
    #     endpoint="/image-to-image",
    #     volume_to_requests_conversion=10,
    #     is_stream=False,
    #     weight=0.1,
    #     timeout=15,
    # ),
    # Task.dreamshaper_image_to_image: FullTaskConfig(
    #     task=Task.dreamshaper_image_to_image,
    #     max_capacity=2_000,
    #     scoring_config=TaskScoringConfig(
    #         task=Task.dreamshaper_image_to_image, mean=0.21, variance=5, overhead=0.5, task_type=TaskType.IMAGE
    #     ),
    #     orchestrator_server_config=OrchestratorServerConfig(
    #         checking_server_needed=ServerType.IMAGE,
    #         checking_load_model_config={},
    #         checking_function="check_image_result",
    #     ),
    #     synthetic_generation_config=SyntheticGenerationConfig(
    #         func="generate_image_to_image_synthetic",
    #         kwargs={"model": Task.dreamshaper_image_to_image.value},
    #     ),
    #     endpoint="/image-to-image",
    #     volume_to_requests_conversion=10,
    #     is_stream=False,
    #     weight=0.1,
    #     timeout=15,
    # ),
    # Task.proteus_image_to_image: FullTaskConfig(
    #     task=Task.proteus_image_to_image,
    #     max_capacity=2_000,
    #     scoring_config=TaskScoringConfig(
    #         task=Task.proteus_image_to_image, mean=0.21, variance=5, overhead=0.5, task_type=TaskType.IMAGE
    #     ),
    #     orchestrator_server_config=OrchestratorServerConfig(
    #         checking_server_needed=ServerType.IMAGE,
    #         checking_load_model_config={},
    #         checking_function="check_image_result",
    #     ),
    #     synthetic_generation_config=SyntheticGenerationConfig(
    #         func="generate_image_to_image_synthetic",
    #         kwargs={"model": Task.proteus_image_to_image.value},
    #     ),
    #     endpoint="/image-to-image",
    #     volume_to_requests_conversion=10,
    #     is_stream=False,
    #     weight=0.1,
    #     timeout=15,
    # ),
    Task.avatar: FullTaskConfig(
        task=Task.avatar,
        max_capacity=2_000,
        scoring_config=TaskScoringConfig(
            task=Task.avatar, mean=0.21, variance=5, overhead=0.5, task_type=TaskType.IMAGE
        ),
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
    ),
    Task.inpaint: FullTaskConfig(
        task=Task.inpaint,
        max_capacity=1,
        scoring_config=TaskScoringConfig(
            task=Task.inpaint, mean=0.21, variance=5, overhead=0.5, task_type=TaskType.IMAGE
        ),
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
    ),
}
