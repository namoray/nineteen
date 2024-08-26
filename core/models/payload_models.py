from typing import Any
from pydantic import BaseModel, Field
from core.models import utility_models
from core.tasks import Task


class CapacityResponse(BaseModel):
    capacities: dict[str, float]


class TextToSpeechRequest(BaseModel):
    params: dict[str, Any]


class ChatPayload(BaseModel):
    messages: list[utility_models.Message] = Field(...)
    temperature: float = Field(default=..., title="Temperature", description="Temperature for text generation.")
    max_tokens: int = Field(500, title="Max Tokens", description="Max tokens for text generation.")
    seed: int = Field(default=..., title="Seed", description="Seed for text generation.")
    model: Task = Field(default=Task.chat_llama_3_1_8b, title="Model")
    top_p: float = Field(default=1.0, title="Top P", description="Top P for text generation.")
    stream: bool = True
    logprobs: bool = True

    class Config:
        use_enum_values = True

class ImageResponse(BaseModel):
    image_b64: str | None
    is_nsfw: bool | None
    clip_embeddings: list[float] | None
    image_hashes: utility_models.ImageHashes | None

class TextToImageRequest(BaseModel):
    prompt: str = Field(...)
    negative_prompt: str | None = Field(
        None, title="Negative Prompt", description="Negative Prompt for text generation."
    )
    seed: int = Field(0, title="Seed", description="Seed for text generation.")
    steps: int = Field(10, title="Steps", description="Steps for text generation.")
    cfg_scale: float = Field(3, title="CFG Scale", description="CFG Scale for text generation.")
    width: int = Field(1024, title="Width", description="Width for text generation.")
    height: int = Field(1024, title="Height", description="Height for text generation.")
    model: str = Field(default=Task.proteus_text_to_image.value, title="Model")





class ImageToImageRequest(BaseModel):
    prompt: str = Field(...)
    negative_prompt: str | None = Field(
        None, title="Negative Prompt", description="Negative Prompt for text generation."
    )
    seed: int = Field(0, title="Seed", description="Seed for text generation.")
    steps: int = Field(10, title="Steps", description="Steps for text generation.")
    cfg_scale: float = Field(3, title="CFG Scale", description="CFG Scale for text generation.")
    width: int = Field(1024, title="Width", description="Width for text generation.")
    height: int = Field(1024, title="Height", description="Height for text generation.")
    image_strength: float = Field(0.5, title="Image Strength", description="Image Strength for text generation.")
    model: str = Field(default=Task.proteus_text_to_image.value, title="Model")
    init_image: str = Field(...)


class InpaintRequest(BaseModel):
    prompt: str = Field(...)
    negative_prompt: str | None = Field(
        None, title="Negative Prompt", description="Negative Prompt for text generation."
    )
    seed: int = Field(0, title="Seed", description="Seed for text generation.")
    steps: int = Field(10, title="Steps", description="Steps for text generation.")
    cfg_scale: float = Field(3, title="CFG Scale", description="CFG Scale for text generation.")
    width: int = Field(1024, title="Width", description="Width for text generation.")
    height: int = Field(1024, title="Height", description="Height for text generation.")
    init_image: str = Field(..., title="Init Image")
    mask_image: str = Field(..., title="Mask Image")

class AvatarRequest(BaseModel):
    prompt: str = Field(...)
    negative_prompt: str | None = Field(
        None, title="Negative Prompt", description="Negative Prompt for text generation."
    )
    seed: int = Field(0, title="Seed", description="Seed for text generation.")
    steps: int = Field(10, title="Steps", description="Steps for text generation.")
    width: int = Field(1024, title="Width", description="Width for text generation.")
    height: int = Field(1024, title="Height", description="Height for text generation.")
    ipadapter_strength: float = Field(0.5, title="Image Adapter Strength", description="Image Adapter Strength for text generation.")
    control_strength: float = Field(0.5, title="Control Strength", description="Control Strength for text generation.")
    init_image: str = Field(..., title="Init Image")