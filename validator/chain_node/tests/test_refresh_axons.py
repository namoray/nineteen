import unittest

from asyncpg import Connection
from validator.db.src.database import PSQLDB
from src.refresh_axons import Config, get_and_store_axons
import bittensor as bt
from core.bittensor_overrides.chain_data import AxonInfo


class TestRefreshAxons(unittest.IsolatedAsyncioTestCase):
    def create_test_config(self) -> Config:
        config = Config(
            psql_db=PSQLDB(),
            run_once=True,
            test_env=True,
            network="test",
            netuid=1,
            seconds_between_syncs=60,
            metagraph=bt.metagraph,
            sync=False,
            subtensor=None,
        )
        self.set_axons_for_testing(config)
        return config

    def set_axons_for_testing(self, config: Config) -> None:
        config.metagraph.network = "test_network"
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

    async def asyncSetUp(self):
        self.config = self.create_test_config()
        await self.config.psql_db.connect()

    async def asyncTearDown(self):
        await self.config.psql_db.close()

    async def test_get_and_store_axons(self):
        async with await self.config.psql_db.connection() as conn:
            conn: Connection


            await conn.execute("DELETE FROM node; DELETE FROM node_history;")

            await get_and_store_axons(self.config)

            node = await conn.fetch("SELECT * FROM node ORDER BY hotkey")
            self.assertEqual(len(node), 3, "Expected 3 axons in node table")

            self.assertEqual(node[0]["hotkey"], "test-hotkey1")
            self.assertEqual(node[1]["hotkey"], "test-hotkey2")
            self.assertEqual(node[2]["hotkey"], "test-vali")

            await get_and_store_axons(self.config)

            axon_history = await conn.fetch("SELECT * FROM node_history ORDER BY hotkey")
            self.assertEqual(len(axon_history), 3, "Expected 3 entries in node_history table")


if __name__ == "__main__":
    unittest.main()
