import asyncio
import os

from redis.asyncio import Redis

from core.logging import get_logger

from validator.db.src.sql.nodes import get_vali_ss58_address
from validator.query_node.src.query_config import Config
from validator.query_node.src.process_queries import listen_for_tasks
from validator.db.src.database import PSQLDB
from dotenv import load_dotenv


logger = get_logger(__name__)
load_dotenv()


async def load_config() -> Config:
    netuid = os.getenv("NETUID")
    if netuid is None:
        raise ValueError("NETUID must be set")
    else:
        netuid = int(netuid)

    psql_db = PSQLDB()
    await psql_db.connect()

    ss58_address = None
    while ss58_address is None:
        ss58_address = await get_vali_ss58_address(psql_db, netuid)
        await asyncio.sleep(0.1)

    return Config(redis_db=Redis(host="redis"), psql_db=psql_db, netuid=netuid, ss58_address=ss58_address)


async def main() -> None:
    config = await load_config()

    await asyncio.gather(
        listen_for_tasks(config),
    )


if __name__ == "__main__":
    asyncio.run(main())
