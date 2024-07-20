from typing import Tuple, TypeVar

from core import bittensor_overrides as bt

from mining.proxy import core_miner
from mining.proxy.operations import abstract_operation
from models import base_models, synapses
from operation_logic import avatar_logic

operation_name = "AvatarOperation"

T = TypeVar("T", bound=bt.Synapse)


class AvatarOperation(abstract_operation.Operation):
    @staticmethod
    async def forward(synapse: synapses.Avatar) -> synapses.Avatar:
        output = await avatar_logic.avatar_logic(base_models.AvatarIncoming(**synapse.dict()))

        synapse.init_image = None

        output_dict = output.dict()
        for field in output_dict:
            setattr(synapse, field, output_dict[field])

        return synapse

    @staticmethod
    async def blacklist(synapse: synapses.Avatar) -> Tuple[bool, str]:
        return core_miner.base_blacklist(synapse)

    @staticmethod
    async def priority(synapse: synapses.Avatar) -> float:
        return core_miner.base_priority(synapse)
