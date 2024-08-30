import json
import httpx
from fiber.logging_utils import get_logger

from core.models import payload_models

logger = get_logger(__name__)

# TODO: fix
LLAMA_3_8B_ADDRESS = "http://62.169.159.78:8000/v1/chat/completions"


async def chat_stream(httpx_client: httpx.AsyncClient, decrypted_payload: payload_models.ChatPayload):
    if True:
        # TODO: review timeout
        async with httpx_client.stream(
            "POST", LLAMA_3_8B_ADDRESS, json=decrypted_payload.model_dump(), timeout=3
        ) as resp:
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
