"""
The naming convention is super important to adhere too!

Keep it as SynapseNameBase / SynapseNameIncoming / SynapseNameOutgoing
"""

from typing import Any
from pydantic import BaseModel, Field
from core.models import utility_models


class CapacityResponse(BaseModel):
    capacities: dict[str, float]


class TextToSpeechRequest(BaseModel):
    params: dict[str, Any]


class ChatRequest(BaseModel):
    messages: list[utility_models.Message] = Field(...)
    temperature: float = Field(default=..., title="Temperature", description="Temperature for text generation.")
    max_tokens: int = Field(500, title="Max Tokens", description="Max tokens for text generation.")
    seed: int = Field(default=..., title="Seed", description="Seed for text generation.")
    model: utility_models.ChatModels = Field(default=..., title="Model")
    top_p: float = Field(default=1.0, title="Top P", description="Top P for text generation.")

    class Config:
        use_enum_values = True
