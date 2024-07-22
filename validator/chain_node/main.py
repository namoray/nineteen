import asyncio
from core.logging import get_logger

from set_weights import main as set_weights_main
from sync_metagraph import main as sync_metagraph_main

logger = get_logger(__name__)


async def main():
    await asyncio.gather(set_weights_main(), sync_metagraph_main())


if __name__ == "__main__":
    asyncio.run(main())
