import asyncio
import os

from redis.asyncio import Redis

from core.logging import get_logger

from validator.query_node.src.query_config import Config
from validator.query_node.src.process_queries import listen_for_tasks
from validator.db.src.database import PSQLDB
from dotenv import load_dotenv


logger = get_logger(__name__)
load_dotenv()


def load_config() -> Config:
    netuid = os.getenv("NETUID")
    if netuid is None:
        raise ValueError("NETUID must be set")
    else:
        netuid = int(netuid)

    return Config(
        psql_db=PSQLDB(),
        redis_db=Redis(host="redis"),
        netuid=netuid,
    )


async def main() -> None:
    config = load_config()
    await config.psql_db.connect()

    await asyncio.gather(
        listen_for_tasks(config),
    )

if __name__ == "__main__":
    asyncio.run(main())