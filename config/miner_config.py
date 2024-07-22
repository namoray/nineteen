from dotenv import load_dotenv
from models import config_models
import os
import argparse
from core.logging import get_logger

logger = get_logger(__name__)

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
    logger.error(f"Could not find env file: {env_file}")
load_dotenv(env_file, verbose=True)


config = config_models.MinerConfig()
