import json
import logging
import os
import sys
from validator.signing_service.src import constants as cst
from substrateinterface import Keypair

ANSI_COLOR_CODES = {
    "$BLUE": "\033[34m",
    "$RESET": "\033[0m",
    "$COLOR": "\033[37m",  # Default to white, you might want to adjust this
    "$BOLD": "\033[1m",
}


def replace_color_codes(message: str) -> str:
    for code, ansi in ANSI_COLOR_CODES.items():
        message = message.replace(code, ansi)
    return message


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        return replace_color_codes(message)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name.split(".")[-1])
    mode: str = os.getenv("ENV", "prod")
    logger.setLevel(logging.DEBUG if mode != "prod" else logging.INFO)
    logger.handlers.clear()

    format_string = (
        "$BLUE%(asctime)s.%(msecs)03d$RESET | "
        "$COLOR$BOLD%(levelname)-8s$RESET | "
        "$BLUE%(name)s$RESET:"
        "$BLUE%(funcName)s$RESET:"
        "$BLUE%(lineno)d$RESET - "
        "$COLOR$BOLD%(message)s$RESET"
    )

    colored_formatter = ColoredFormatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(colored_formatter)
    logger.addHandler(console_handler)

    logger.debug(f"Mode is {mode}")
    return logger


logger = get_logger(__name__)


def construct_wallet_path(wallet_name: str, hotkey_name: str) -> str:
    return f"/root/.bittensor/wallets/{wallet_name}/hotkeys/{hotkey_name}"


def load_keypair_from_file(file_path: str):
    try:
        with open(file_path, "r") as file:
            keypair_data = json.load(file)
        keypair = Keypair.create_from_seed(keypair_data["secretSeed"])
        logger.info(f"Loaded keypair from {file_path}")
        return keypair
    except Exception as e:
        raise ValueError(f"Failed to load keypair: {str(e)}")


def construct_signed_message_key(job_id: str) -> str:
    return f"{cst.SIGNED_MESSAGES_KEY}:{job_id}"
