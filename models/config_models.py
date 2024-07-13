import os

from pydantic import BaseModel
from core import constants as ccst


class CoreConfig(BaseModel):
    hotkey_name: str = os.getenv(ccst.HOTKEY_PARAM, "default")
    wallet_name: str = os.getenv(ccst.WALLET_NAME_PARAM, "default")

    subtensor_network: str = os.getenv(ccst.SUBTENSOR_NETWORK_PARAM, "finney")
    subtensor_chainendpoint: str | None = os.getenv(ccst.SUBTENSOR_CHAINENDPOINT_PARAM, None)
    is_validator: bool


class MinerConfig(CoreConfig):
    image_worker_url: str | None = os.getenv(ccst.IMAGE_WORKER_URL_PARAM, None)
    mixtral_text_worker_url: str | None = os.getenv(ccst.MIXTRAL_TEXT_WORKER_URL_PARAM, None)
    llama_3_text_worker_url: str | None = os.getenv(ccst.LLAMA_3_TEXT_WORKER_URL_PARAM, None)

    axon_port: str = os.getenv(ccst.AXON_PORT_PARAM, 8012)
    axon_external_ip: str = os.getenv(ccst.AXON_EXTERNAL_IP_PARAM, "127.0.0.1")

    debug_miner: bool = os.getenv(ccst.DEBUG_MINER_PARAM, False)
    is_validator: bool = False


class ValidatorConfig(CoreConfig):
    external_server_url: str = os.getenv(ccst.EXTERNAL_SERVER_ADDRESS_PARAM, None)
    api_server_port: int | None = os.getenv(ccst.API_SERVER_PORT_PARAM, None)
    is_validator: bool = True
