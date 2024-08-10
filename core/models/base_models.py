"""
The naming convention is super important to adhere too!

Keep it as SynapseNameBase / SynapseNameIncoming / SynapseNameOutgoing
"""

from typing import Any
from pydantic import BaseModel

from core.tasks import Task


class CapacityForTask(BaseModel):
    volume: float


class CapacityResponse(BaseModel):
    capacities: dict[Task | str, CapacityForTask] | None


class TextToSpeechRequest(BaseModel):
    params: dict[str, Any]
