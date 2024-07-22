# Still need to do calculations then send to redis


import asyncio
from validator.core.calculate_weights import calculations
from validator.db.database import PSQLDB
from validator.db import sql

from core.logging import get_logger

logger = get_logger(__name__)
async def main():
    psql_db = PSQLDB()
    await psql_db.connect()

    async with await psql_db.connection() as connection:
        participants = await sql.fetch_all_participants(connection, None)
    scores = await calculations.calculate_scores_for_settings_weights(psql_db, participants)

    logger.debug(f"scores: {scores}")
    return scores


if __name__ == "__main__":
    asyncio.run(main())
