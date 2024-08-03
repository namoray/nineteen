import asyncio
import unittest
from unittest.mock import patch
import time
from redis.asyncio import Redis
from validator.db.src.database import PSQLDB
from validator.utils import redis_constants as rcst
from validator.control_center.src.schedule_synthetics import ( 
    Config,
    schedule_synthetic_query,
    schedule_synthetics_until_done,
)


class TestSyntheticSchedulerFunctional(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Use actual Redis instance for functional testing
        self.redis_db = Redis(host="redis", port=6379, db=0)
        self.psql_db = PSQLDB()
        await self.psql_db.connect()

        self.config = Config(
            psql_db=self.psql_db, redis_db=self.redis_db, run_once=False, test_env=True, specific_participant=None
        )

        # Clear Redis before each test
        await self.redis_db.flushdb()

    async def asyncTearDown(self):
        await self.redis_db.aclose()
        await self.psql_db.close()

    @patch("validator.utils.participant_utils.add_synthetic_query_to_queue")
    async def test_schedule_and_process_synthetics(self, mock_add_to_queue):
        participant_id = "test_participant"
        num_synthetics = 10
        delay = 1.0

        # Schedule 10 synthetic queries
        for _ in range(num_synthetics):
            await schedule_synthetic_query(self.redis_db, participant_id, delay)

        # Verify that 10 items are in the queue
        queue_size = await self.redis_db.zcard(rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY)
        self.assertEqual(
            queue_size, num_synthetics, f"Expected {num_synthetics} items in queue, but found {queue_size}"
        )

        # Run the scheduler
        start_time = time.time()

        async def stop_after_timeout():
            await asyncio.sleep(15)  # Allow 15 seconds for processing
            self.config.run_once = True

        await asyncio.gather(schedule_synthetics_until_done(self.config), stop_after_timeout())

        end_time = time.time()

        # Verify that all items were processed
        queue_size_after = await self.redis_db.zcard(rcst.SYNTHETIC_SCHEDULING_QUEUE_KEY)
        self.assertEqual(
            queue_size_after, 0, f"Expected 0 items in queue after processing, but found {queue_size_after}"
        )

        # Verify that add_synthetic_query_to_queue was called for each synthetic
        self.assertEqual(
            mock_add_to_queue.call_count,
            num_synthetics,
            f"Expected add_synthetic_query_to_queue to be called {num_synthetics} times, but was called {mock_add_to_queue.call_count} times",
        )

        # Verify that processing took at least (num_synthetics * delay) seconds
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
