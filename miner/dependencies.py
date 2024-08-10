from miner import config


def get_config(hotkey: str) -> config.Config:
    return config.factory_config()
