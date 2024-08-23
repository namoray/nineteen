


from validator.entry_node.src.core.configuration import Config
from validator.entry_node.src.core import configuration


async def get_config() -> Config:
    return await configuration.factory_config()