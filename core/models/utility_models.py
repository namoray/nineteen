import enum
from typing import List, Optional, Any

from pydantic import BaseModel

from core.tasks import Task

class ChatModels(str, enum.Enum):
    """Model is used for the chat"""

    mixtral = "mixtral-8x7b"
    llama_3 = "llama-3"
    llama_31_8b = "llama-3-1-8b"
    llama_31_70b = "llama-3-1-70b"


class QueryResult(BaseModel):
    formatted_response: Any
    axon_uid: Optional[int]
    miner_hotkey: Optional[str]
    response_time: Optional[float]
    error_message: Optional[str]
    failed_axon_uids: List[int] = []
    task: Task
    status_code: Optional[int]
    success: bool
