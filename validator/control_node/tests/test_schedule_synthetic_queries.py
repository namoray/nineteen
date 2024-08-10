import unittest
from redis.asyncio import Redis
from core.tasks import Task
from validator.db.src.database import PSQLDB
from validator.db.src import sql
from validator.models import Participant
from validator.utils import redis_constants as rcst
from validator.control_node.src.schedule_synthetic_queries import (
    Config,
    schedule_synthetics_until_done,
)


class TestSyntheticSchedulerFunctional(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.redis_db = Redis(host="redis", port=6379, db=0)
        self.psql_db = PSQLDB()
        await self.psql_db.connect()

        self.config = Config(
            psql_db=self.psql_db, redis_db=self.redis_db, run_once=False, test_env=True, specific_participant=None
        )

        await self.redis_db.flushdb()

    async def asyncTearDown(self):
        await self.redis_db.aclose()
        await self.psql_db.close()

    async def test_schedule_and_process_synthetics(
        self,
    ):
        num_synthetics = 3
        delay = 1.0
        participant = Participant(
            miner_hotkey="test_hotkey",
            miner_uid=0,
            task=Task.chat_llama_3,
            synthetic_requests_still_to_make=num_synthetics,
            delay_between_synthetic_requests=delay,
            raw_capacity=10000,
            capacity=100,
            consumed_capacity=0,
            capacity_to_score=100,
            total_requests_made=0,
        )

        async with await self.psql_db.connection() as connection:
            await connection.execute("DELETE FROM participants")
            await sql.insert_participants(connection, [participant], "test_vali")

        await schedule_synthetics_until_done(self.config)

        self.assertEqual(await self.redis_db.get(rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY), None)


if __name__ == "__main__":
    unittest.main()
