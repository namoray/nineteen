from miner.core import config
from miner.core.models import Config


def get_config(hotkey: str) -> Config:
    return config.factory_config()
