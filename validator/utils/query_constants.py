from models import synapses
from dataclasses import dataclass

@dataclass
class Timeouts:
    connect_timeout: int
    response_timeout: int
# Dodgy
OPERATION_TIMEOUTS: dict[str, Timeouts] = {
    "Capacity": Timeouts(connect_timeout=10, response_timeout=5),
    synapses.TextToImage.__class__.__name__: Timeouts(connect_timeout=1, response_timeout=10),
    synapses.ImageToImage.__class__.__name__: Timeouts(connect_timeout=1, response_timeout=12),
    "Chat": Timeouts(connect_timeout=0.5, response_timeout=5)
}
