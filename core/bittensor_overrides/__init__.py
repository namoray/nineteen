from core.bittensor_overrides.axon import axon
from core.bittensor_overrides.synapse import Synapse, TerminalInfo
from core.bittensor_overrides.chain_data import AxonInfo
from core.bittensor_overrides.stream import StreamingSynapse
from core.bittensor_overrides.utils import networking
from core.bittensor_overrides.dendrite import dendrite
from core.bittensor_overrides.config import config


__all__ = ["dendrite", "axon", "Synapse", "AxonInfo", "StreamingSynapse", "networking", "config", "TerminalInfo"]


__version__ = "7.3.0"

_version_split = __version__.split(".")
__version_info__ = tuple(int(part) for part in _version_split)
_version_int_base = 1000
assert max(__version_info__) < _version_int_base

__version_as_int__: int = sum(e * (_version_int_base**i) for i, e in enumerate(reversed(__version_info__)))
assert __version_as_int__ < 2**31  # fits in int32
