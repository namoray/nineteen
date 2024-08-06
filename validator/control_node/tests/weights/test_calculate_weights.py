import unittest
from unittest.mock import patch, AsyncMock
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

    # ... (keep existing tests)

    def test_apply_non_linear_transformation(self):
        scores = {
            "hotkey1": 0.5,
            "hotkey2": 0.8,
            "hotkey3": 0.2,
        }
        result = calculations.apply_non_linear_transformation(scores)
        
        self.assertAlmostEqual(result["hotkey1"], 0.125, places=3)  # 0.5^3
        self.assertAlmostEqual(result["hotkey2"], 0.512, places=3)  # 0.8^3
        self.assertAlmostEqual(result["hotkey3"], 0.008, places=3)  # 0.2^3

    @patch("validator.control_node.src.weights.calculations.calculate_effective_volumes_for_task")
    @patch("validator.control_node.src.weights.calculations.normalize_scores_for_task")
    async def test_calculate_scores_for_settings_weights_with_non_linear_transformation(
        self, mock_normalize_scores, mock_calculate_volumes
    ):
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
                miner_uid=2,
                miner_hotkey="hotkey2",
                task=Task.chat_mixtral,
                capacity=300,
                raw_capacity=1500,
                consumed_capacity=0,
                capacity_to_score=150,
                delay_between_synthetic_requests=1,
                synthetic_requests_still_to_make=10,
            ),
        ]

        mock_calculate_volumes.return_value = {
            "hotkey1": 100.0,
            "hotkey2": 150.0,
        }

        mock_normalize_scores.return_value = {
            "hotkey1": 0.4,
            "hotkey2": 0.6,
        }

        # Mocking the task weights
        with patch("validator.control_node.src.weights.calculations.tcfg.TASK_TO_CONFIG", {
            Task.chat_llama_3: AsyncMock(weight=0.5),
            Task.chat_mixtral: AsyncMock(weight=0.5),
        }):
            result = await calculations.calculate_scores_for_settings_weights(self.psql_db, participants)

        self.assertIn(1, result)
        self.assertIn(2, result)
        
        # The exact values will depend on the non-linear transformation and normalization
        # Here we're just checking that the scores are present and sum to 1
        self.assertGreater(result[1], 0)
        self.assertGreater(result[2], 0)
        self.assertAlmostEqual(sum(result.values()), 1.0, places=6)

        # Verify that the non-linear transformation was applied
        mock_normalize_scores.assert_called()
        args, _ = mock_normalize_scores.call_args
        transformed_volumes = args[0]
        self.assertAlmostEqual(transformed_volumes["hotkey1"], 1000000, places=0)  # 100^3
        self.assertAlmostEqual(transformed_volumes["hotkey2"], 3375000, places=0)  # 150^3

    @patch("validator.control_node.src.weights.calculations.calculate_effective_volumes_for_task")
    async def test_calculate_scores_for_settings_weights_integration(self, mock_calculate_volumes):
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
                miner_uid=2,
                miner_hotkey="hotkey2",
                task=Task.chat_mixtral,
                capacity=300,
                raw_capacity=1500,
                consumed_capacity=0,
                capacity_to_score=150,
                delay_between_synthetic_requests=1,
                synthetic_requests_still_to_make=10,
            ),
        ]

        mock_calculate_volumes.side_effect = [
            {"hotkey1": 100.0, "hotkey2": 0.0},  # For chat_llama_3
            {"hotkey1": 0.0, "hotkey2": 150.0},  # For chat_mixtral
        ]

        # Mocking the task weights
        with patch("validator.control_node.src.weights.calculations.tcfg.TASK_TO_CONFIG", {
            Task.chat_llama_3: AsyncMock(weight=0.5),
            Task.chat_mixtral: AsyncMock(weight=0.5),
        }):
            result = await calculations.calculate_scores_for_settings_weights(self.psql_db, participants)

        self.assertIn(1, result)
        self.assertIn(2, result)
        self.assertAlmostEqual(sum(result.values()), 1.0, places=6)

        # Due to the non-linear transformation, the scores should be more skewed
        # than a simple 50-50 split, but still sum to 1
        self.assertGreater(result[1], 0.4)
        self.assertGreater(result[2], 0.4)

if __name__ == "__main__":
    unittest.main()
