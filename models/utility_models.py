import enum
from typing import Dict, List, Optional, Any

import numpy as np
from pydantic import BaseModel
import bittensor as bt

from core import Task
from validation.models import AxonUID

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


class ChatModels(str, enum.Enum):
    """Model is used for the chat"""

    mixtral = "mixtral-8x7b"
    llama_3 = "llama-3"


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


class HotkeyInfo(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    uid: AxonUID
    hotkey: str
    axon: bt.chain_data.AxonInfo


class OperationDistribution(BaseModel):
    available_axons: List[int]
    probabilities: List[float]
    score_discounts: Dict[int, float]

    def get_order_of_axons_to_query(self) -> List[int]:
        z = -np.log(-np.log(np.random.uniform(0, 1, len(self.available_axons))))
        scores = np.log(self.probabilities) + z
        return [self.available_axons[i] for i in np.argsort(-scores)]


class EngineEnum(str, enum.Enum):
    DREAMSHAPER = "dreamshaper"
    PLAYGROUND = "playground"
    PROTEUS = "proteus"


class ImageHashes(BaseModel):
    average_hash: str = ""
    perceptual_hash: str = ""
    difference_hash: str = ""
    color_hash: str = ""


class ImageResponseBody(BaseModel):
    image_b64: Optional[str] = None
    is_nsfw: Optional[bool] = None
    clip_embeddings: Optional[List[float]] = None
    image_hashes: Optional[ImageHashes] = None


class MinerChatResponse(BaseModel):
    text: str
    logprob: float
