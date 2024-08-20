"""
The naming convention is super important to adhere too!

Keep it as SynapseNameBase / SynapseNameIncoming / SynapseNameOutgoing
"""

from typing import Any
from pydantic import BaseModel, Field
from core.models import utility_models
from core.tasks import Task


class CapacityResponse(BaseModel):
    capacities: dict[str, float]

class TextToSpeechRequest(BaseModel):
    params: dict[str, Any]


class ChatRequest(BaseModel):
    messages: list[utility_models.Message] = Field(...)
    temperature: float = Field(default=..., title="Temperature", description="Temperature for text generation.")
    max_tokens: int = Field(500, title="Max Tokens", description="Max tokens for text generation.")
    seed: int = Field(default=..., title="Seed", description="Seed for text generation.")
    model: Task = Field(default=Task.chat_llama_3_1_8b, title="Model")
    top_p: float = Field(default=1.0, title="Top P", description="Top P for text generation.")

    class Config:
        use_enum_values = True

class TextToImageRequest(BaseModel):
    prompt: str = Field(...)
    negative_prompt: str | None = Field(None, title="Negative Prompt", description="Negative Prompt for text generation.")
    seed: int = Field(0, title="Seed", description="Seed for text generation.")
    steps: int = Field(10, title="Steps", description="Steps for text generation.")
    cfg_scale: float = Field(3, title="CFG Scale", description="CFG Scale for text generation.")
    width: int = Field(1024, title="Width", description="Width for text generation.")
    height: int = Field(1024, title="Height", description="Height for text generation.")
    model: Task = Field(default=Task.proteus_text_to_image, title="Model")