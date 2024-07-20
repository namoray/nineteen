from typing import Optional

from pydantic import BaseModel


class Model(BaseModel):
    class Config:
        arbitrary_types_allowed = True


class TextPrompt(BaseModel):
    text: str
    weight: Optional[float]
