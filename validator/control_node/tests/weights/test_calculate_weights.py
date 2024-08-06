import unittest
from unittest.mock import patch
from datetime import datetime
from redis.asyncio import Redis
from validator.db.src.database import PSQLDB
from validator.models import Participant, RewardData, PeriodScore
from validator.control_node.src.weights import calculations
from core.tasks import Task
from core.logging import get_logger

logger = get_logger(__name__)


class TestWeightsCalculationFunctional(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.redis_db = Redis(host="redis", port=6379, db=0)
        self.psql_db = PSQLDB()
        await self.psql_db.connect()

    async def asyncTearDown(self):
        await self.redis_db.aclose()
        await self.psql_db.close()

    @patch("validator.db.src.functions.fetch_recent_most_rewards_for_uid")
    @patch("validator.db.src.functions.fetch_hotkey_scores_for_task")
    async def test_calculate_scores_with_multiple_tasks(self, mock_fetch_scores, mock_fetch_rewards):
        participants = [
            Participant(
                miner_uid=1,
                miner_hotkey="hotkey1",
                task=Task.chat_llama_3,
                capacity=200,
                raw_capacity=1000,
                consumed_capacity=0,
                capacity_to_score=100,
                delay_between_synthetic_requests=1,
                synthetic_requests_still_to_make=10,
            ),
            Participant(
                miner_uid=1,
                miner_hotkey="hotkey1",
                task=Task.chat_mixtral,
                capacity=200,
                raw_capacity=1000,
                consumed_capacity=0,
                capacity_to_score=100,
                delay_between_synthetic_requests=1,
                synthetic_requests_still_to_make=10,
            ),
            Participant(
                miner_uid=2,
                miner_hotkey="hotkey2",
                task=Task.chat_mixtral,
                capacity=200,
                raw_capacity=1000,
                consumed_capacity=0,
                capacity_to_score=100,
                delay_between_synthetic_requests=1,
                synthetic_requests_still_to_make=10,
            ),
        ]

        mock_rewards = [
            RewardData(
                id="reward1",
                task="chat_llama_3",
                axon_uid=1,
                quality_score=0.8,
                validator_hotkey="validator1",
                miner_hotkey="hotkey1",
                synthetic_query=False,
                speed_scoring_factor=1.0,
                response_time=0.5,
                volume=100.0,
                created_at=datetime.now(),
            ),
            RewardData(
                id="reward2",
                task="chat_mixtral",
                axon_uid=2,
                quality_score=0.9,
                validator_hotkey="validator1",
                miner_hotkey="hotkey2",
                synthetic_query=False,
                speed_scoring_factor=1.0,
                response_time=0.4,
                volume=150.0,
                created_at=datetime.now(),
            ),
        ]

        mock_scores = [
            PeriodScore(
                hotkey="hotkey1",
                task=Task.chat_llama_3,
                period_score=0.1,
                consumed_capacity=50,
                created_at=datetime.now(),
            ),
            PeriodScore(
                hotkey="hotkey1",
                task=Task.chat_mixtral,
                period_score=0.8,
                consumed_capacity=100,
                created_at=datetime.now(),
            ),
            PeriodScore(
                hotkey="hotkey2",
                task=Task.chat_llama_3,
                period_score=0.8,
                consumed_capacity=100,
                created_at=datetime.now(),
            ),
        ]

        mock_fetch_rewards.return_value = mock_rewards
        mock_fetch_scores.return_value = mock_scores

        result = await calculations.calculate_scores_for_settings_weights(self.psql_db, participants)

        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 2)
        self.assertIn(1, result)
        self.assertIn(2, result)

        total_score = sum(result.values())
        self.assertAlmostEqual(total_score, 1.0, places=2)

        logger.debug(f"result: {result}")

        mock_fetch_rewards.assert_called()
        mock_fetch_scores.assert_called()


if __name__ == "__main__":
    unittest.main()
