from fibre.miner.core import config
from fibre.miner.core.models.config import Config


def get_config() -> Config:
    return config.factory_config()
