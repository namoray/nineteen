"""
An example of what your custom tasks config file might look like.
Make a file called custom_task_config.py ( touch core/custom_task_config.py )
and add code similar to this to extend your task configs.
"""

from core.models import config_models as cmodels
from core.task_config import (
    CHAT_LLAMA_3_2_3B,
    task_configs_factory,
)
from core.utils import get_updated_task_config_with_voted_weights

CHAT_LLAMA_3_1_405B = "chat_llama_3_1_405b"


def custom_task_configs_factory():
    # This uses all the standard configs as base.
    base_task_config = task_configs_factory()
    # Except i might decide that I'm not interested now in the 8b model
    del base_task_config[CHAT_LLAMA_3_2_3B]

    # Now I will add the model I do want
    addition = {
        CHAT_LLAMA_3_1_405B: cmodels.FullTaskConfig(
            task=CHAT_LLAMA_3_1_405B,
            task_type=cmodels.TaskType.TEXT,
            max_capacity=4_000_000,  # I can also change the capacity however I like
            orchestrator_server_config=cmodels.OrchestratorServerConfig(
                server_needed=cmodels.ServerType.LLM,
                load_model_config={
                    "model": "hugging-quants/Meta-Llama-3.1-405B-Instruct-GPTQ-INT4",  # This should exist on hugging face else it wont work
                    "half_precision": True,
                    "tokenizer": "llama-tokenizer-fix",  # This should be the tokenizer you like. Usually the base tokenizer, except for Llama's
                    "num_gpus": 4,
                    "tensor_parallel_size": 4,
                    "max_model_len": 16_000,
                    "gpu_utilization": 0.8,
                },
                endpoint=cmodels.Endpoints.chat_completions.value,
                checking_function="check_text_result",
                task=CHAT_LLAMA_3_1_405B,
            ),
            synthetic_generation_config=cmodels.SyntheticGenerationConfig(
                func="generate_chat_synthetic", kwargs={"model": CHAT_LLAMA_3_1_405B}
            ),
            endpoint=cmodels.Endpoints.chat_completions.value,
            volume_to_requests_conversion=300,
            is_stream=True,
            weight=0.20,
            timeout=2,
            enabled=True,
        )
    }

    combined_config = base_task_config | addition
    # Optionally use the voted weights to help set consensus
    combined_config = get_updated_task_config_with_voted_weights(combined_config)
    return combined_config
