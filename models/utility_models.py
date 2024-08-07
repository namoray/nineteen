from typing import List, Optional, Any

from pydantic import BaseModel

from core.tasks import Task


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
