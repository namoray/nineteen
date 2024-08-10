from raycoms.miner.core import config
from raycoms.miner.core.models.config import Config


def get_config() -> Config:
    return config.factory_config()
