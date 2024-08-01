import asyncio
import logging
from unittest.mock import MagicMock
from core.bittensor_overrides.chain_data import AxonInfo
from src.refresh_axons import Config, get_and_store_axons
from validator.db.src.database import PSQLDB
import unittest


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestRefreshAxons(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_get_and_store_axons(self):
        async def run_test():
            config = self.create_test_config()
            await config.psql_db.connect()

            # Run once
            await get_and_store_axons(config)
            result = await self.get_axon_info(config)
            self.assertEqual(len(result), 3)

            # Run twice
            await get_and_store_axons(config)
            history = await self.get_axon_history(config)
            self.assertEqual(len(history), 3)

        self.loop.run_until_complete(run_test())

    def test_get_and_store_axons_db_error(self):
        async def run_test():
            config = self.create_test_config()
            config.psql_db.connect = MagicMock(side_effect=Exception("DB Connection Error"))
            with self.assertRaises(Exception):
                await get_and_store_axons(config)

        self.loop.run_until_complete(run_test())

    def create_test_config(self):
        config = Config(
            psql_db=PSQLDB(),
            run_once=True,
            test_env=True,
            network="test",
            netuid=1,
            seconds_between_syncs=60,
            metagraph=MagicMock(),
            sync=False,
            subtensor=None,
        )
        self.set_axons_for_testing(config)
        return config

    def set_axons_for_testing(self, config: Config) -> None:
        config.metagraph = MagicMock()
        config.metagraph.network = "test_network"  # Use a string instead of MagicMock
        config.metagraph.netuid = 1
        config.metagraph.axons = [
            AxonInfo(
                version=1,
                ip="127.0.0.1",
                port=1,
                ip_type=4,
                hotkey="test-vali",
                coldkey="test-vali-ck",
                axon_uid=0,
                incentive=0,
                netuid=config.metagraph.netuid,
                network=config.metagraph.network,
                stake=50.0,
            ),
            AxonInfo(
                version=1,
                ip="127.0.0.1",
                port=1,
                ip_type=4,
                hotkey="test-hotkey1",
                coldkey="test-coldkey1",
                axon_uid=1,
                incentive=0.004,
                netuid=config.metagraph.netuid,
                network=config.metagraph.network,
                stake=30.0,
            ),
            AxonInfo(
                version=2,
                ip="127.0.0.1",
                port=2,
                ip_type=4,
                hotkey="test-hotkey2",
                coldkey="test-coldkey2",
                axon_uid=2,
                incentive=0.005,
                netuid=config.metagraph.netuid,
                network=config.metagraph.network,
                stake=20.0,
            ),
        ]
        config.metagraph.total_stake = [50, 30, 20]
        config.sync = False

    async def get_axon_info(self, config):
        async with await config.psql_db.connection() as conn:
            return await conn.fetch("SELECT * FROM axon_info")

    async def get_axon_history(self, config):
        async with await config.psql_db.connection() as conn:
            return await conn.fetch("SELECT * FROM axon_info_history")


if __name__ == "__main__":
    unittest.main()
