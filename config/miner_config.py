from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional
from core import constants as ccst
import os
import bittensor as bt
import argparse


def _get_env_file_from_cli_config() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env_file", type=str, default=None)
    args, _ = parser.parse_known_args()
    env_file = args.env_file

    if not env_file:
        parser.error("You didn't specify an env file! Use --env_file to specify it.")

    return env_file


env_file = _get_env_file_from_cli_config()
if not os.path.exists(env_file):
    bt.logging.error(f"Could not find env file: {env_file}")
load_dotenv(env_file, verbose=True)


class Config(BaseModel):
    hotkey_name: str = os.getenv(ccst.HOTKEY_PARAM, "default")
    wallet_name: str = os.getenv(ccst.WALLET_NAME_PARAM, "default")

    subtensor_network: str = os.getenv(ccst.SUBTENSOR_NETWORK_PARAM, "finney")
    subtensor_chainendpoint: Optional[str] = os.getenv(ccst.SUBTENSOR_CHAINENDPOINT_PARAM, None)

    image_worker_url: Optional[str] = os.getenv(ccst.IMAGE_WORKER_URL_PARAM, None)
    mixtral_text_worker_url: Optional[str] = os.getenv(ccst.MIXTRAL_TEXT_WORKER_URL_PARAM, None)
    llama_3_text_worker_url: Optional[str] = os.getenv(ccst.LLAMA_3_TEXT_WORKER_URL_PARAM, None)

    axon_port: str = os.getenv(ccst.AXON_PORT_PARAM, 8012)
    axon_external_ip: str = os.getenv(ccst.AXON_EXTERNAL_IP_PARAM, "127.0.0.1")

    debug_miner: bool = os.getenv(ccst.DEBUG_MINER_PARAM, False)


config = Config()
