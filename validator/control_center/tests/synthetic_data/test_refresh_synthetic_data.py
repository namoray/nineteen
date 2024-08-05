import asyncio
import unittest
from redis.asyncio import Redis
from core.tasks import Task
from validator.db.src.database import PSQLDB
from validator.utils import redis_constants as rcst
from validator.utils import synthetic_utils as sutils
from validator.control_center.src.synthetic_data.refresh_synthetic_data import update_tasks_synthetic_data


class TestSyntheticDataStorageFunctional(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.redis_db = Redis(host="redis", port=6379, db=0)
        self.psql_db = PSQLDB()
        await self.psql_db.connect()

        await self.redis_db.flushdb()

    async def asyncTearDown(self):
        await self.redis_db.aclose()
        await self.psql_db.close()

    async def test_update_tasks_synthetic_data(self):
        await update_tasks_synthetic_data(self.redis_db, slow_sync=False)

        for task in Task:
            task_key = sutils.construct_synthetic_data_task_key(task)
            synthetic_data = await self.redis_db.get(task_key)
            self.assertIsNotNone(synthetic_data)

            version = await self.redis_db.hget(rcst.SYNTHETIC_DATA_VERSIONS_KEY, task.value)
            self.assertIsNotNone(version)

    async def test_update_specific_task_synthetic_data(self):
        for task in Task:
            specific_task = task
            await update_tasks_synthetic_data(self.redis_db, slow_sync=False, task=specific_task)

            task_key = sutils.construct_synthetic_data_task_key(specific_task)
            synthetic_data = await self.redis_db.get(task_key)
            self.assertIsNotNone(synthetic_data)

            version = await self.redis_db.hget(rcst.SYNTHETIC_DATA_VERSIONS_KEY, specific_task.value)
            self.assertIsNotNone(version)

    async def test_continuously_fetch_synthetic_data(self):
        async def mock_continuous_fetch():
            await update_tasks_synthetic_data(self.redis_db, slow_sync=False)
            await asyncio.sleep(2)
            await update_tasks_synthetic_data(self.redis_db, slow_sync=True)

        await asyncio.wait_for(mock_continuous_fetch(), timeout=5)

        for task in Task:
            task_key = sutils.construct_synthetic_data_task_key(task)
            synthetic_data = await self.redis_db.get(task_key)
            self.assertIsNotNone(synthetic_data)

            version = await self.redis_db.hget(rcst.SYNTHETIC_DATA_VERSIONS_KEY, task.value)
            self.assertIsNotNone(version)


if __name__ == "__main__":
    unittest.main()
