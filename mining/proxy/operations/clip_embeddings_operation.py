from typing import Tuple, TypeVar

from core import bittensor_overrides as bt

from mining.proxy import core_miner
from mining.proxy.operations import abstract_operation
from models import base_models, synapses
from operation_logic import clip_embeddings_logic

# Make sure this matches the class name
operation_name = "ClipEmbeddingsOperation"

T = TypeVar("T", bound=bt.Synapse)


class ClipEmbeddingsOperation(abstract_operation.Operation):
    @staticmethod
    async def forward(synapse: synapses.ClipEmbeddings) -> synapses.ClipEmbeddings:
        output = await clip_embeddings_logic.clip_embeddings_logic(base_models.ClipEmbeddingsIncoming(**synapse.dict()))

        synapse.image_b64s = None

        output_dict = output.dict()
        for field in output_dict:
            setattr(synapse, field, output_dict[field])

        return synapse

    @staticmethod
    def blacklist(synapse: synapses.ClipEmbeddings) -> Tuple[bool, str]:
        return core_miner.base_blacklist(synapse)

    @staticmethod
    def priority(synapse: synapses.ClipEmbeddings) -> float:
        return core_miner.base_priority(synapse)
