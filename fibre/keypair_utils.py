import json
from pathlib import Path
from substrateinterface import Keypair
from fibre.logging_utils import get_logger

logger = get_logger(__name__)


def construct_wallet_path(wallet_name: str, hotkey_name: str) -> Path:
    return Path.home() / ".bittensor" / "wallets" / wallet_name / "hotkeys" / hotkey_name


def load_keypair_from_file(file_path: str):
    try:
        with open(file_path, "r") as file:
            keypair_data = json.load(file)
        keypair = Keypair.create_from_seed(keypair_data["secretSeed"])
        logger.info(f"Loaded keypair from {file_path}")
        return keypair
    except Exception as e:
        raise ValueError(f"Failed to load keypair: {str(e)}")
