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


class ChatModels(str, enum.Enum):
    """Model is used for the chat"""


    llama_31_8b = "llama-3-1-8b"
    llama_31_70b = "llama-3-1-70b"


class QueryResult(BaseModel):
    formatted_response: Any
    node_id: Optional[int]
    node_hotkey: Optional[str]
    response_time: Optional[float]
    task: Task
    status_code: Optional[int]
    success: bool
