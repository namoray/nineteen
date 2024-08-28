import base64
import random
from fastapi import HTTPException
import httpx
from pydantic import BaseModel, Field
from core.models import utility_models
from core.tasks import Task
from core.models import payload_models
from core.logging import get_logger
from validator.utils.entry_utils import image_b64_is_valid, fetch_image_b64

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


class TextToImageRequest(BaseModel):
    prompt: str = Field(...)
    negative_prompt: str | None = Field(None, title="Negative Prompt", description="Negative Prompt for text generation.")
    steps: int = Field(10, title="Steps", description="Steps for text generation.")
    cfg_scale: float = Field(3, title="CFG Scale", description="CFG Scale for text generation.")
    width: int = Field(1024, title="Width", description="Width for text generation.")
    height: int = Field(1024, title="Height", description="Height for text generation.")
    model: str = Field(default=Task.proteus_text_to_image.value, title="Model")


def text_to_image_to_payload(text_to_image_request: TextToImageRequest) -> payload_models.TextToImagePayload:
    return payload_models.TextToImagePayload(
        **text_to_image_request.model_dump(),
        seed=random.randint(1, 100000),
    )


class ImageToImageRequest(BaseModel):
    init_image: str = Field(
        ...,
        description="Base64 encoded image",
        examples=["https://lastfm.freetls.fastly.net/i/u/770x0/443c5e1c35fd38bb5a49a7d00612dab3.jpg#443c5e1c35fd38bb5a49a7d00612dab3", "iVBORw0KGgoAAAANSUhEUgAAAAUA"],
    )
    prompt: str = Field(..., examples=["A beautiful landscape with a river and mountains", "A futuristic city with flying cars"])
    negative_prompt: str | None = Field(None, title="Negative Prompt", description="Negative Prompt for text generation.")
    steps: int = Field(10, title="Steps", description="Steps for text generation.")
    cfg_scale: float = Field(3, title="CFG Scale", description="CFG Scale for text generation.")
    width: int = Field(1024, title="Width", description="Width for text generation.")
    height: int = Field(1024, title="Height", description="Height for text generation.")
    model: str = Field(default=Task.proteus_image_to_image.value, title="Model")


async def image_to_image_to_payload(image_to_image_request: ImageToImageRequest, httpx_client: httpx.AsyncClient, prod: bool) -> payload_models.ImageToImagePayload:
    if "https://" in image_to_image_request.init_image:
        image_b64 = await fetch_image_b64(image_to_image_request.init_image)
    else:
        if not image_b64_is_valid(image_to_image_request.init_image):
            raise HTTPException(status_code=400, detail="Invalid init image!")
        image_b64 = image_to_image_request.init_image
    return payload_models.ImageToImagePayload(
        init_image=image_b64,
        prompt=image_to_image_request.prompt,
        negative_prompt=image_to_image_request.negative_prompt,
        steps=image_to_image_request.steps,
        cfg_scale=image_to_image_request.cfg_scale,
        width=image_to_image_request.width,
        height=image_to_image_request.height,
        model=image_to_image_request.model,
        seed=random.randint(1, 100000),
    )


class ImageResponse(BaseModel):
    image_b64: str
