from typing import Dict, Optional
from core import Task
from mining.db.db_management import miner_db_manager
import bittensor as bt

from models import synapses, utility_models


# Would people want this to be in a DB instead which is read on every request, but then more configurable?
def load_concurrency_groups(hotkey: str) -> Dict[str, float]:
    return miner_db_manager.load_concurrency_groups()


def load_capacities(hotkey: str) -> Dict[str, Dict[str, float]]:
    return miner_db_manager.load_task_capacities(hotkey)


def get_task_from_synapse(synapse: bt.Synapse) -> Optional[Task]:
    if isinstance(synapse, synapses.Chat):
        if synapse.model == utility_models.ChatModels.mixtral.value:
            return Task.chat_mixtral
        elif synapse.model == utility_models.ChatModels.llama_3.value:
            return Task.chat_llama_3
        else:
            return None
    elif isinstance(synapse, synapses.TextToImage):
        if synapse.engine == utility_models.EngineEnum.PROTEUS.value:
            return Task.proteus_text_to_image
        elif synapse.engine == utility_models.EngineEnum.PLAYGROUND.value:
            return Task.playground_text_to_image
        elif synapse.engine == utility_models.EngineEnum.DREAMSHAPER.value:
            return Task.dreamshaper_text_to_image
        else:
            return None
    elif isinstance(synapse, synapses.ImageToImage):
        if synapse.engine == utility_models.EngineEnum.PROTEUS.value:
            return Task.proteus_image_to_image
        elif synapse.engine == utility_models.EngineEnum.PLAYGROUND.value:
            return Task.playground_image_to_image
        elif synapse.engine == utility_models.EngineEnum.DREAMSHAPER.value:
            return Task.dreamshaper_image_to_image
        else:
            return None
    elif isinstance(synapse, synapses.Inpaint):
        return Task.jugger_inpainting
    # elif isinstance(synapse, synapses.ClipEmbeddings):
    #     return Task.clip_image_embeddings
    elif isinstance(synapse, synapses.Avatar):
        return Task.avatar
    else:
        return None
