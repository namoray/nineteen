import unittest
from unittest.mock import patch, AsyncMock
from redis.asyncio import Redis
from validator.db.src.database import PSQLDB
from validator.models import Contender
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

    def test_normalize_scores_for_task(self):
        volumes = {
            "hotkey1": 100.0,
            "hotkey2": 200.0,
            "hotkey3": 300.0,
        }
        result = calculations.normalize_scores_for_task(volumes)

        self.assertAlmostEqual(result["hotkey1"], 1 / 6, places=6)
        self.assertAlmostEqual(result["hotkey2"], 1 / 3, places=6)
        self.assertAlmostEqual(result["hotkey3"], 1 / 2, places=6)

    @patch("validator.control_node.src.weights.calculations.calculate_effective_volumes_for_task")
    async def test_calculate_scores_for_settings_weights_with_double_normalization(self, mock_calculate_volumes):
        contenders = [
            Contender(
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
            Contender(
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
        with patch(
            "validator.control_node.src.weights.calculations.tcfg.TASK_TO_CONFIG",
            {
                Task.chat_llama_3: AsyncMock(weight=0.5),
                Task.chat_mixtral: AsyncMock(weight=0.5),
            },
        ):
            result = await calculations.calculate_scores_for_settings_weights(self.psql_db, contenders)

        self.assertIn(1, result)
        self.assertIn(2, result)
        self.assertAlmostEqual(sum(result.values()), 1.0, places=6)

        # Due to the double normalization and non-linear transformation,
        # the scores should be closer to 0.5 each than with a single normalization
        self.assertGreater(result[1], 0.4)
        self.assertLess(result[1], 0.6)
        self.assertGreater(result[2], 0.4)
        self.assertLess(result[2], 0.6)

        logger.debug(f"Final scores: {result}")

    @patch("validator.control_node.src.weights.calculations.calculate_effective_volumes_for_task")
    async def test_calculate_scores_for_settings_weights_integration(self, mock_calculate_effective_volumes):
        contenders = [
            Contender(
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
            Contender(
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
            Contender(
                miner_uid=2,
                miner_hotkey="hotkey2",
                task=Task.chat_llama_3,
                capacity=300,
                raw_capacity=1500,
                consumed_capacity=0,
                capacity_to_score=150,
                delay_between_synthetic_requests=1,
                synthetic_requests_still_to_make=10,
            ),
        ]

        mock_calculate_effective_volumes.side_effect = [
            {"hotkey1": 50.0, "hotkey2": 100.0},  # For chat_llama_3
            {"hotkey1": 100.0, "hotkey2": 0},  # For chat_mixtral
        ]

        # Mocking the task weights
        with patch(
            "validator.control_node.src.weights.calculations.tcfg.TASK_TO_CONFIG",
            {
                Task.chat_llama_3: AsyncMock(weight=0.5),
                Task.chat_mixtral: AsyncMock(weight=0.5),
            },
        ):
            result = await calculations.calculate_scores_for_settings_weights(self.psql_db, contenders)

        self.assertIn(1, result)
        self.assertIn(2, result)
        self.assertAlmostEqual(sum(result.values()), 1.0, places=6)

        logger.debug(f"Result: {result}")

        # Due to the double normalization and non-linear transformation,
        # the scores should be more balanced than with a single normalization
        self.assertGreater(result[1], 0.4)
        self.assertGreater(result[2], 0.2)
        self.assertLess(result[1] / result[2], 2.5)  # The ratio should be less extreme

    @patch("validator.control_node.src.weights.calculations._calculate_combined_quality_score")
    @patch("validator.control_node.src.weights.calculations._calculate_normalised_period_score")
    async def test_calculate_effective_volumes_for_task(self, mock_normalised_score, mock_quality_score):
        contenders = [
            Contender(
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
            Contender(
                miner_uid=2,
                miner_hotkey="hotkey2",
                task=Task.chat_llama_3,
                capacity=300,
                raw_capacity=1500,
                consumed_capacity=0,
                capacity_to_score=150,
                delay_between_synthetic_requests=1,
                synthetic_requests_still_to_make=10,
            ),
        ]

        # Mock the quality scores and normalised period scores
        mock_quality_score.side_effect = [0.8, 0.9]
        mock_normalised_score.side_effect = [0.7, 0.6]

        result = await calculations.calculate_effective_volumes_for_task(self.psql_db, contenders, Task.chat_llama_3)

        self.assertIn("hotkey1", result)
        self.assertIn("hotkey2", result)
        
        # Expected effective volumes:
        # hotkey1: 0.8 * 0.7 * 200 = 112
        # hotkey2: 0.9 * 0.6 * 300 = 162
        self.assertAlmostEqual(result["hotkey1"], 112.0, places=1)
        self.assertAlmostEqual(result["hotkey2"], 162.0, places=1)

        # Check that the mocked functions were called with the correct contenders
        mock_quality_score.assert_any_call(self.psql_db, contenders[0])
        mock_quality_score.assert_any_call(self.psql_db, contenders[1])
        mock_normalised_score.assert_any_call(self.psql_db, contenders[0])
        mock_normalised_score.assert_any_call(self.psql_db, contenders[1])



if __name__ == "__main__":
    unittest.main()
