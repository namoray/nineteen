from typing import Tuple, TypeVar

from core import bittensor_overrides as bt

from mining.proxy import core_miner
from mining.proxy.operations import abstract_operation
from models import base_models, synapses
from operation_logic import upscale_logic

operation_name = "UpscaleOperation"

T = TypeVar("T", bound=bt.Synapse)


class UpscaleOperation(abstract_operation.Operation):
    @staticmethod
    async def forward(synapse: synapses.Upscale) -> synapses.Upscale:
        output = await upscale_logic.upscale_logic(base_models.UpscaleIncoming(**synapse.dict()))

        synapse.image = None

        output_dict = output.dict()
        for field in output_dict:
            setattr(synapse, field, output_dict[field])
        return synapse

    @staticmethod
    async def blacklist(synapse: synapses.Upscale) -> Tuple[bool, str]:
        return core_miner.base_blacklist(synapse)

    @staticmethod
    async def priority(synapse: synapses.Upscale) -> float:
        return core_miner.base_priority(synapse)
