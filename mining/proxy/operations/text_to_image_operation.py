from typing import Tuple, TypeVar

from core import bittensor_overrides as bt

from mining.proxy import core_miner
from mining.proxy.operations import abstract_operation
from models import base_models, synapses
from operation_logic import text_to_image_logic

operation_name = "TextToImageOperation"

T = TypeVar("T", bound=bt.Synapse)


class TextToImageOperation(abstract_operation.Operation):
    @staticmethod
    @abstract_operation.enforce_concurrency_limits
    async def forward(synapse: synapses.TextToImage) -> synapses.TextToImage:
        output = await text_to_image_logic.text_to_image_logic(base_models.TextToImageIncoming(**synapse.dict()))
        output_dict = output.dict()
        for field in output_dict:
            setattr(synapse, field, output_dict[field])

        return synapse

    @staticmethod
    def blacklist(synapse: synapses.TextToImage) -> Tuple[bool, str]:
        return core_miner.base_blacklist(synapse)

    @staticmethod
    def priority(synapse: synapses.TextToImage) -> float:
        return core_miner.base_priority(synapse)
