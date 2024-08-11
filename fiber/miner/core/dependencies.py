from fiber.miner.core import config
from fiber.miner.core.models.config import Config


def get_config() -> Config:
    return config.factory_config()
