from typing import Tuple, TypeVar

from core import bittensor_overrides as bt

from mining.proxy import core_miner
from mining.proxy.operations import abstract_operation
from models import base_models, synapses
from operation_logic import image_to_image_logic

operation_name = "ImageToImageOperation"

T = TypeVar("T", bound=bt.Synapse)


class ImageToImageOperation(abstract_operation.Operation):
    @staticmethod
    async def forward(synapse: synapses.ImageToImage) -> synapses.ImageToImage:
        output = await image_to_image_logic.image_to_image_logic(base_models.ImageToImageIncoming(**synapse.dict()))

        synapse.init_image = None

        output_dict = output.dict()
        for field in output_dict:
            setattr(synapse, field, output_dict[field])

        return synapse

    @staticmethod
    async def blacklist(synapse: synapses.ImageToImage) -> Tuple[bool, str]:
        return core_miner.base_blacklist(synapse)

    @staticmethod
    async def priority(synapse: synapses.ImageToImage) -> float:
        return core_miner.base_priority(synapse)
