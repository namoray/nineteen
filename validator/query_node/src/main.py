from dotenv import load_dotenv
import os

# Must be done straight away, bit ugly
load_dotenv(os.getenv("ENV_FILE", ".dev.env"))

import asyncio 
from redis.asyncio import Redis 

from core.logging import get_logger 

from validator.db.src.sql.nodes import get_vali_ss58_address
from validator.query_node.src.query_config import Config
from validator.query_node.src.process_queries import listen_for_tasks
from validator.db.src.database import PSQLDB

logger = get_logger(__name__)


async def load_config() -> Config:
    netuid = os.getenv("NETUID")
    if netuid is None:
        raise ValueError("NETUID must be set")
    else:
        netuid = int(netuid)

    localhost = bool(os.getenv("LOCALHOST", "false").lower() == "true")
    if localhost:
        redis_host = "localhost"
        os.environ["POSTGRES_HOST"] = "localhost"
    else:
        redis_host = os.getenv("REDIS_HOST", "redis")

    replace_with_docker_localhost = bool(os.getenv("REPLACE_WITH_DOCKER_LOCALHOST", "false").lower() == "true")

    psql_db = PSQLDB()
    await psql_db.connect()

    ss58_address = None
    while ss58_address is None:
        ss58_address = await get_vali_ss58_address(psql_db, netuid)
        await asyncio.sleep(0.1)

    return Config(
        redis_db=Redis(host=redis_host),
        psql_db=psql_db,
        netuid=netuid,
        ss58_address=ss58_address,
        replace_with_docker_localhost=replace_with_docker_localhost,
        replace_with_localhost=localhost,
    )


async def main() -> None:
    config = await load_config()
    logger.debug(f"config: {config}")
    await asyncio.gather(
        listen_for_tasks(config),
    )


if __name__ == "__main__":
    asyncio.run(main())
