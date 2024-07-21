import json
import logging
import os
import sys
from validator.signing_service import constants as cst
from substrateinterface import Keypair
import random
import time

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


def retry(
    f,
    logger,
    exceptions=Exception,
    tries=-1,
    delay=0,
    max_delay=None,
    backoff=1,
    jitter=0,
):
    """
    Executes a function and retries it if it failed.

    :param f: the function to execute.
    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param tries: the maximum number of attempts. default: -1 (infinite).
    :param delay: initial delay between attempts. default: 0.
    :param max_delay: the maximum value of delay. default: None (no limit).
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :param logger: logger.warning(fmt, error, delay) will be called on failed attempts.
                   default: retry.logging_logger. if None, logging is disabled.
    :returns: the result of the f function.
    """
    _tries, _delay = tries, delay
    while _tries:
        try:
            return f()
        except exceptions as e:
            _tries -= 1
            if not _tries:
                raise

            if logger is not None:
                logger.warning("%s, retrying in %s seconds...", e, _delay)

            time.sleep(_delay)
            _delay *= backoff

            if isinstance(jitter, tuple):
                _delay += random.uniform(*jitter)
            else:
                _delay += jitter

            if max_delay is not None:
                _delay = min(_delay, max_delay)


def format_weights_error_message(error_message: dict) -> str:
    """
    Formats an error message from the Subtensor error information to using in extrinsics.

    Args:
        error_message (dict): A dictionary containing the error information from Subtensor.

    Returns:
        str: A formatted error message string.
    """
    err_type = "UnknownType"
    err_name = "UnknownError"
    err_description = "Unknown Description"

    if isinstance(error_message, dict):
        err_type = error_message.get("type", err_type)
        err_name = error_message.get("name", err_name)
        err_docs = error_message.get("docs", [])
        err_description = err_docs[0] if len(err_docs) > 0 else err_description
    return f"Subtensor returned `{err_name} ({err_type})` error. This means: `{err_description}`"


def construct_wallet_path(wallet_name: str, hotkey_name: str) -> str:
    return f"/root/.bittensor/wallets/{wallet_name}/hotkeys/{hotkey_name}"


def construct_signed_message_key(job_id: str) -> str:
    return f"{cst.SIGNED_MESSAGES_KEY}:{job_id}"


def load_keypair_from_file(file_path: str):
    try:
        with open(file_path, "r") as file:
            keypair_data = json.load(file)
        keypair = Keypair.create_from_seed(keypair_data["secretSeed"])
        logger.info(f"Loaded keypair from {file_path}")
        return keypair
    except Exception as e:
        raise ValueError(f"Failed to load keypair: {str(e)}")
