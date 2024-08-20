import enum
from typing import Optional, Any

from pydantic import BaseModel
from core.tasks import Task


class Role(str, enum.Enum):
    """Message is sent by which role?"""

    user = "user"
    assistant = "assistant"
    system = "system"


class Message(BaseModel):
    role: Role = Role.user
    content: str = "Remind me that I have forgot to set the messages"

    class Config:
        extra = "allow"


class QueryResult(BaseModel):
    formatted_response: Any
    node_id: Optional[int]
    node_hotkey: Optional[str]
    response_time: Optional[float]
    task: Task
    status_code: Optional[int]
    success: bool


class ImageHashes(BaseModel):
    average_hash: str = ""
    perceptual_hash: str = ""
    difference_hash: str = ""
    color_hash: str = ""
