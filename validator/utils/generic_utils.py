import base64
import contextlib
import logging
import time
from typing import AsyncGenerator

from PIL import Image
import io

from core.logging import get_logger

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


async def async_chain(first_chunk: str, async_gen: str) -> AsyncGenerator[str]:
    yield first_chunk  # manually yield the first chunk
    async for item in async_gen:
        yield item  # then yield from the original generator