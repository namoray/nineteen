import random
from pydantic import BaseModel, Field
from core.models import utility_models
from core.tasks import Task
from core.models import payload_models
from core.logging import get_logger

logger = get_logger(__name__)

class ChatRequest(BaseModel):
    messages: list[utility_models.Message] = Field(...)
    temperature: float = Field(default=..., title="Temperature", description="Temperature for text generation.")
    max_tokens: int = Field(500, title="Max Tokens", description="Max tokens for text generation.")
    model: Task = Field(default=Task.chat_llama_3_1_8b, title="Model")
    top_p: float = Field(default=1.0, title="Top P", description="Top P for text generation.")
    stream: bool = True
    logprobs: bool = True

    class Config:
        use_enum_values = True


def chat_to_payload(chat_request: ChatRequest) -> payload_models.ChatPayload:
    return payload_models.ChatPayload(
        messages=chat_request.messages,
        temperature=chat_request.temperature,
        max_tokens=chat_request.max_tokens,
        model=chat_request.model,
        top_p=chat_request.top_p,
        stream=chat_request.stream,
        logprobs=chat_request.logprobs,
        seed=random.randint(1, 100000),
    )
