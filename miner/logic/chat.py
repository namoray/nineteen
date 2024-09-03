import json
import httpx
from fiber.logging_utils import get_logger

from core.models import payload_models
from core import tasks_config as tcfg

logger = get_logger(__name__)

# TODO: fix
LLAMA_3_8B_ADDRESS = "http://94.156.8.15:8000/v1/chat/completions"
LLAMA_3_70B_ADDRESS = "http://94.156.8.15:8001/v1/chat/completions"


async def chat_stream(httpx_client: httpx.AsyncClient, decrypted_payload: payload_models.ChatPayload):
    # TODO: tidy
    task_config = tcfg.get_enabled_task_config(decrypted_payload.model)
    if task_config is None:
        raise ValueError(f"Task config not found for model: {decrypted_payload.model}")
    model_name = task_config.orchestrator_server_config.load_model_config["model"]
    decrypted_payload.model = model_name

    if decrypted_payload.model == "unsloth/Meta-Llama-3.1-8B-Instruct":
        address = LLAMA_3_8B_ADDRESS
    elif decrypted_payload.model == "hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4":
        address = LLAMA_3_70B_ADDRESS
    else:
        raise ValueError(f"Invalid model: {decrypted_payload.model}")

    if True:
        # TODO: review timeout
        async with httpx_client.stream("POST", address, json=decrypted_payload.model_dump(), timeout=3) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_lines():
                try:
                    received_event_chunks = chunk.split("\n\n")
                    for event in received_event_chunks:
                        if event == "":
                            continue
                        prefix, _, data = event.partition(":")
                        if data.strip() == "[DONE]":
                            break
                        yield f"data: {data}\n\n"
                except Exception as e:
                    logger.error(f"Error in streaming text from the server: {e}. Original chunk: {chunk}")
    else:
        for i in range(100):
            data = {"choices": [{"delta": {"content": f"{i}"}}]}
            yield f"data: {json.dumps(data)}\n\n"
        yield "data: [DONE]\n\n"
