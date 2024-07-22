from pydantic import BaseModel, Field, root_validator, validator
from typing import Optional, List
from models import utility_models
import random
from core import constants as cst, dataclasses as dc

ALLOWED_PARAMS_FOR_ENGINE = {
    utility_models.EngineEnum.PROTEUS.value: {
        "steps": {
            "checker": lambda x: isinstance(x, int) and x in range(6, 13),
            "error_message": "should be an integer between 6 and 12 (inclusive)",
        },
        "height": {
            "checker": lambda h: 512 <= h <= 1344 and h % 64 == 0,
            "error_message": "should be in between 512 and 1344 (inclusive) and multiple of 64",
        },
        "width": {
            "checker": lambda w: 512 <= w <= 1344 and w % 64 == 0,
            "error_message": "should be in between 512 and 1344 (inclusive) and multiple of 64",
        },
        "cfg_scale": {"checker": lambda c: 1 <= c <= 4, "error_message": "should be between 1 and 4"},
        "image_strength": {"checker": lambda i: 0.0 <= i <= 0.75, "error_message": "should be between 0.0 and 0.75"},
    },
    utility_models.EngineEnum.DREAMSHAPER.value: {
        "steps": {
            "checker": lambda x: isinstance(x, int) and x in range(6, 13),
            "error_message": "should be an integer between 6 and 12 (inclusive)",
        },
        "height": {
            "checker": lambda h: 512 <= h <= 1344 and h % 64 == 0,
            "error_message": "should be in between 512 and 1344 (inclusive) and multiple of 64",
        },
        "width": {
            "checker": lambda w: 512 <= w <= 1344 and w % 64 == 0,
            "error_message": "should be in between 512 and 1344 (inclusive) and multiple of 64",
        },
        "cfg_scale": {"checker": lambda c: 1 <= c <= 4, "error_message": "should be between 1 and 4"},
        "image_strength": {"checker": lambda i: 0.0 <= i <= 0.75, "error_message": "should be between 0.0 and 0.75"},
    },
    utility_models.EngineEnum.PLAYGROUND.value: {
        "steps": {
            "checker": lambda x: isinstance(x, int) and x in range(25, 51),
            "error_message": "should be an integer between 25 and 51 (inclusive)",
        },
        "height": {
            "checker": lambda h: 512 <= h <= 1344 and h % 64 == 0,
            "error_message": "should be in between 512 and 1344 (inclusive) and multiple of 64",
        },
        "width": {
            "checker": lambda w: 512 <= w <= 1344 and w % 64 == 0,
            "error_message": "should be in between 512 and 1344 (inclusive) and multiple of 64",
            "generator": lambda: random.choice([i for i in range(512, 1344 + 64, 64)]),
        },
        "cfg_scale": {"checker": lambda c: 1 <= c <= 10, "error_message": "should be between 1 and 10"},
        "image_strength": {
            "checker": lambda i: 0.0 <= i <= 0.75,
            "error_message": "should be between 0.0 and 0.75",
            "generator": lambda: random.random() * 0.75,
        },
    },
}


class TextToImageRequest(BaseModel):
    """Generate an image from text!"""

    cfg_scale: float = Field(cst.DEFAULT_CFG_SCALE, description="Scale for the configuration", ge=0.1, le=10)
    steps: int = Field(
        cst.DEFAULT_STEPS, description="Number of steps in the image generation process - must be an ", le=50, ge=1
    )
    engine: utility_models.EngineEnum = Field(
        default=utility_models.EngineEnum.PROTEUS.value, description="The engine to use for image generation"
    )

    text_prompts: List[dc.TextPrompt] = Field(..., description="Prompts for the image generation", title="text_prompts")
    height: Optional[int] = Field(cst.DEFAULT_HEIGHT, description="Height of the generated image", le=1344, ge=512)
    width: Optional[int] = Field(cst.DEFAULT_WIDTH, description="Width of the generated image", le=1344, ge=512)

    class Config:
        schema_extra = {
            "examples": [
                {
                    "text_prompts": [{"text": "A dog parachuting over the ocean"}],
                    "height": 1280,
                    "width": 1280,
                    "engine": "proteus",
                    "steps": 8,
                    "cfg_scale": 2.0,
                }
            ]
        }
        use_enum_values = True
        extra = "forbid"

    @validator("text_prompts")
    def check_text_prompts_non_empty(cls, values):
        if not values:
            raise ValueError("Text prompts cannot be empty")
        return values

    # @root_validator
    # def allowed_params_validator(cls, values):
    #     engine = values.get("engine")
    #     steps = values.get("steps")
    #     height = values.get("height")
    #     width = values.get("width")
    #     cfg_scale = values.get("cfg_scale")

    #     params_and_values = [("steps", steps), ("height", height), ("width", width), ("cfg_scale", cfg_scale)]

    #     if engine not in ALLOWED_PARAMS_FOR_ENGINE:
    #         raise ValueError(f"Engine {engine} not supported")
    #     allowed_params = ALLOWED_PARAMS_FOR_ENGINE[engine]
    #     for param, value in params_and_values:
    #         if param not in allowed_params or value is None:
    #             continue
    #         checker = allowed_params[param]["checker"]
    #         if not checker(value):
    #             error_message = allowed_params[param]["error_message"]
    #             raise ValueError(
    #                 f"Invalid value {value} provided for {param}, with engine {engine}. The value {error_message}"
    #             )

    #     return values


class ImageToImageRequest(BaseModel):
    """Generate an image from another image (+ text)!"""

    class Config:
        use_enum_values = True

    cfg_scale: float = Field(cst.DEFAULT_CFG_SCALE, description="Scale for the configuration", le=10, ge=0.1)
    steps: int = Field(cst.DEFAULT_STEPS, description="Number of steps in the image generation process", le=50, ge=1)
    engine: utility_models.EngineEnum = Field(
        default=utility_models.EngineEnum.PROTEUS.value, description="The engine to use for image generation"
    )

    init_image: str = Field(..., description="The base64 encoded image", title="init_image")
    text_prompts: List[dc.TextPrompt] = Field([], description="Prompts for the image generation", title="text_prompts")

    image_strength: float = Field(0.25, description="The strength of the init image", le=0.9, ge=0.0)

    height: Optional[int] = Field(1024, description="Height of the generated image", le=1344, ge=512)
    width: Optional[int] = Field(1024, description="Width of the generated image", le=1344, ge=512)

    # @validator("text_prompts")
    # def check_text_prompts_non_empty(cls, values):
    #     if not values:
    #         raise ValueError("Text prompts cannot be empty")
    #     return values

    # @root_validator
    # def allowed_params_validator(cls, values):
    #     engine = values.get("engine")
    #     steps = values.get("steps")
    #     height = values.get("height")
    #     width = values.get("width")
    #     cfg_scale = values.get("cfg_scale")

    #     params_and_values = [("steps", steps), ("height", height), ("width", width), ("cfg_scale", cfg_scale)]

    #     if engine not in ALLOWED_PARAMS_FOR_ENGINE:
    #         raise ValueError(f"Engine {engine} not supported")
    #     allowed_params = ALLOWED_PARAMS_FOR_ENGINE[engine]
    #     for param, value in params_and_values:
    #         if param not in allowed_params or value is None:
    #             continue
    #         checker = allowed_params[param]["checker"]
    #         if not checker(value):
    #             error_message = allowed_params[param]["error_message"]
    #             raise ValueError(
    #                 f"Invalid value {value} provided for {param}, with engine {engine}. The value {error_message}"
    #             )

    # return values


class AvatarRequest(BaseModel):
    class Config:
        use_enum_values = True

    text_prompts: List[dc.TextPrompt] = Field(..., description="Prompts for the image generation", title="text_prompts")
    init_image: Optional[str] = Field(..., description="The base64 encoded image", title="image")
    ipadapter_strength: float = Field(0.5, description="The strength of the init image")
    control_strength: float = Field(0.5, description="The strength of the init image")
    height: int = Field(1024, description="Height of the generated image")
    width: int = Field(1024, description="Width of the generated image")
    steps: int = Field(15, description="Number of steps in the image generation process")


class InpaintRequest(BaseModel):
    class Config:
        use_enum_values = True

    cfg_scale: float = Field(cst.DEFAULT_CFG_SCALE, description="Scale for the configuration")
    steps: int = Field(cst.DEFAULT_STEPS, description="Number of steps in the image generation process")

    init_image: str = Field(..., description="The base64 encoded image", title="init_image")
    text_prompts: List[dc.TextPrompt] = Field([], description="Prompts for the image generation", title="text_prompts")

    mask_image: str = Field(None, description="The base64 encoded mask", title="mask_source")

    # @validator("text_prompts")
    # def check_text_prompts_non_empty(cls, values):
    #     if not values:
    #         raise ValueError("Text prompts cannot be empty")
    #     return values


# class ScribbleRequest(BaseModel):
#     """Generate an image from a doodle (+ text)!

#     Supports model with various allowed parameters. Models:

#     - SD-1.5:
#     -- steps: 7 to 25
#     -- height: 512 to 1024 (and multiple of 64)
#     -- width: 512 to 1024 (and multiple of 64)
#     -- cfg_scale: 2 to 8
#     -- image_strength: 0.0 to 0.75
#     """
#     class Config:
#         use_enum_values = True

#     cfg_scale: float = Field(cst.DEFAULT_CFG_SCALE, description="Scale for the configuration")
#     steps: int = Field(cst.DEFAULT_STEPS, description="Number of steps in the image generation process")
#     engine: utility_models.EngineEnum = Field(
#         default=utility_models.EngineEnum.PL.value, description="The engine to use for image generation", const=True
#     )

#     init_image: str = Field(..., description="The base64 encoded image", title="init_image")
#     text_prompts: List[dc.TextPrompt] = Field([], description="Prompts for the image generation", title="text_prompts")

#     engine: utility_models.EngineEnum = Field(utility_models.EngineEnum.SDXL_1_5, const=True)
#     image_strength: float = Field(0.25, description="The strength of the init image")

#     height: Optional[int] = Field(None, description="Height of the generated image")
#     width: Optional[int] = Field(None, description="Width of the generated image")

#     @validator("text_prompts")
#     def check_text_prompts_non_empty(cls, values):
#         if not values:
#             raise ValueError("Text prompts cannot be empty")
#         return values

#     @root_validator
#     def allowed_params_validator(cls, values):

#         engine = values.get('engine')
#         steps = values.get('steps')
#         height = values.get('height')
#         width = values.get('width')
#         cfg_scale = values.get('cfg_scale')

#         params_and_values = [("steps", steps), ("height", height), ("width", width), ("cfg_scale", cfg_scale)]

#         if engine not in ALLOWED_PARAMS_FOR_ENGINE:
#             raise ValueError(f"Engine {engine} not supported")
#         allowed_params = ALLOWED_PARAMS_FOR_ENGINE[engine]
#         for param, value in params_and_values:

#             if param not in allowed_params or value is None:
#                 continue
#             checker = allowed_params[param]['checker']
#             if not checker(value):
#                 error_message = allowed_params[param]['error_message']
#                 raise ValueError(f"Invalid value {value} provided for {param}, with engine {engine}. The value {error_message}")

#         return values


class ChatRequest(BaseModel):
    messages: list[utility_models.Message] = Field(...)
    temperature: float = Field(
        default=..., title="Temperature", description="Temperature for text generation.", ge=0.1, le=1.0
    )

    model: utility_models.ChatModels = Field(
        ...,
        title="Model",
        description="The model to use for text generation.",
    )

    max_tokens: int = Field(500, title="Max Tokens", description="Max tokens for text generation.")


class UpscaleRequest(BaseModel):
    image: str = Field(..., description="The base64 encoded image", title="image")


class ClipEmbeddingsRequest(BaseModel):
    image_b64s: List[str] = Field(
        None,
        description="The image b64s",
        title="image_b64s",
    )


class TextToImageResponse(BaseModel):
    image_b64: str = Field(..., description="The base64 encoded images to return", title="image_b64")


class ImageToImageResponse(BaseModel):
    image_b64: str = Field(..., description="The base64 encoded images to return", title="image_b64")


class InpaintResponse(BaseModel):
    image_b64: str = Field(..., description="The base64 encoded images to return", title="image_b64")


class AvatarResponse(BaseModel):
    image_b64: str = Field(..., description="The base64 encoded images to return", title="image_b64")


class ScribbleResponse(BaseModel):
    image_b64: str = Field(..., description="The base64 encoded images to return", title="image_b64")


class UpscaleResponse(BaseModel):
    image_b64: str = Field(..., description="The base64 encoded images to return", title="image_b64")


class ClipEmbeddingsResponse(BaseModel):
    clip_embeddings: List[List[float]] = Field(..., description="The image embeddings", title="clip_embeddings")
