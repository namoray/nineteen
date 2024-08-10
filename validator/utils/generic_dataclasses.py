from dataclasses import dataclass
from generic.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AxonInfo:
    version: int
    ip: str
    port: int
    ip_type: int
    hotkey: str
    coldkey: str
    axon_uid: int
    incentive: float | None
    netuid: int
    network: str
    stake: float
    protocol: int = 4
    placeholder1: int = 0
    placeholder2: int = 0
