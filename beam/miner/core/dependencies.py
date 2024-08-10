from beam.miner.core import config
from beam.miner.core.models.config import Config


def get_config() -> Config:
    return config.factory_config()
