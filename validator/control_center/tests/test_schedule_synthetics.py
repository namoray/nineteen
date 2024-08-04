import asyncio
import unittest
from unittest.mock import patch
import time
from redis.asyncio import Redis
from core.tasks import Task
from validator.db.src.database import PSQLDB
from validator.db.src import sql
from validator.models import Participant
from validator.utils import redis_constants as rcst
from validator.control_center.src.schedule_synthetics import (
    Config,
    schedule_synthetics_until_done,
)
from datetime import datetime, timedelta


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
        return
        self.assertEqual(
            mock_add_to_queue.call_count,
            num_synthetics,
            f"Expected {num_synthetics} calls to add_synthetic_query_to_queue, but got {mock_add_to_queue.call_count}",
        )

        queue_size = await self.redis_db.zcard(rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY)
        self.assertEqual(
            queue_size,
            num_synthetics,
            f"Expected {num_synthetics} items in queue after processing, but found {queue_size}",
        )

        end_time = datetime.now()
        queue_items = await self.redis_db.zrange(rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY, 0, -1, withscores=True)
        for item, score in queue_items:
            self.assertGreater(score, end_time.timestamp(), "Expected updated timestamp to be in the future")

        # self.assertLess(
        #     end_time - start_time,
        #     timedelta(seconds=num_synthetics * delay + 1),
        #     "Function took longer than expected to complete",
        # )

        async def stop_after_timeout():
            await asyncio.sleep(15)
            self.config.run_once = True

        await asyncio.gather(schedule_synthetics_until_done(self.config), stop_after_timeout())

        end_time = time.time()

        queue_size_after = await self.redis_db.zcard(rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY)
        self.assertEqual(
            queue_size_after, 0, f"Expected 0 items in queue after processing, but found {queue_size_after}"
        )

        self.assertEqual(
            mock_add_to_queue.call_count,
            num_synthetics,
            f"Expected add_synthetic_query_to_queue to be called {num_synthetics} times, but was called {mock_add_to_queue.call_count} times",
        )

        expected_min_duration = num_synthetics * delay
        actual_duration = end_time - start_time
        self.assertGreaterEqual(
            actual_duration,
            expected_min_duration,
            f"Processing took {actual_duration:.2f}s, expected at least {expected_min_duration:.2f}s",
        )

        print(f"Processed {num_synthetics} synthetic queries in {actual_duration:.2f} seconds")


if __name__ == "__main__":
    unittest.main()
