import asyncio
import base64
import contextlib
import logging
import time

from PIL import Image
import io

from redis import Redis
from validator.utils import redis_constants as rcst, redis_dataclasses as rdc
import json
from generic.logging import get_logger

logger = get_logger(__name__)


def pil_to_base64(image: Image, format: str = "JPEG") -> str:
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


@contextlib.contextmanager
def log_time(description: str, logger: logging.Logger):
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.debug(f"{description} took {elapsed_time:.4f} seconds")


# TODO: change this to instead push and pull a message, rather than just checking
async def get_public_keypair_info(redis_db: Redis) -> rdc.PublicKeypairInfo:
    logger.info("Getting public key config from Redis...")
    i = 0
    while i < 10:
        info = await redis_db.get(rcst.PUBLIC_KEYPAIR_INFO_KEY)
        if info is None:
            logger.info("No public key config found in Redis, waiting for 10 secs before trying again...")
            i += 1
            await asyncio.sleep(10)
        else:
            break
    if info is None:
        raise RuntimeError("Could not get public key config from Redis")
    logger.info("Got public key config from Redis!")
    return rdc.PublicKeypairInfo(**json.loads(info))
