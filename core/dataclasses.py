from typing import Optional

from bittensor.chain_data import AxonInfo
from pydantic import BaseModel



class Model(BaseModel):
    class Config:
        arbitrary_types_allowed = True


class Axon(Model):
    index: int
    uid: str
    hotkey: str
    coldkey: str
    incentive: float
    bt_axon: AxonInfo


class TextPrompt(BaseModel):
    text: str
    weight: Optional[float]
