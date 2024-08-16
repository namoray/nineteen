"""
The naming convention is super important to adhere too!

Keep it as SynapseNameBase / SynapseNameIncoming / SynapseNameOutgoing
"""

from typing import Any
from pydantic import BaseModel



class CapacityResponse(BaseModel):
    capacities: dict[str, float]


class TextToSpeechRequest(BaseModel):
    params: dict[str, Any]
