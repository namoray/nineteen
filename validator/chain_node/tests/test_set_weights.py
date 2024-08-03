import unittest
import json
import os
from unittest.mock import patch, MagicMock
from typing import List

from redis.asyncio import Redis
from redis import Redis as SyncRedis
import bittensor as bt

from validator.utils import redis_constants as rcst, generic_utils as gutils
from validator.chain_node.src.keypair import RedisGappedKeypair
from validator.utils import redis_dataclasses as rdc
from validator.chain_node.src.set_weights import Config, poll_for_weights_then_set, set_weights


class TestWeightSetter(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.redis_host = os.getenv("REDIS_HOST", "redis")
        self.redis_db = Redis(host=self.redis_host)
        self.sync_redis = SyncRedis(host=self.redis_host)

        self.config = await self.create_test_config()

    async def asyncTearDown(self):
        await self.redis_db.aclose()
        self.sync_redis.close()

    async def create_test_config(self) -> Config:
        subtensor_network = "test"
        netuid = 176

        public_keypair_info = await gutils.get_public_keypair_info(self.redis_db)
        keypair = RedisGappedKeypair(
            redis_db=self.sync_redis,
            ss58_address=public_keypair_info.ss58_address,
            ss58_format=public_keypair_info.ss58_format,
            crypto_type=public_keypair_info.crypto_type,
            public_key=public_keypair_info.public_key,
        )
        wallet = bt.wallet()
        wallet._hotkey = keypair

        subtensor = bt.subtensor(network=subtensor_network)
        metagraph = subtensor.metagraph(netuid=netuid)

        return Config(
            redis_host=self.redis_host,
            subtensor_network=subtensor_network,
            netuid=netuid,
            redis_db=self.redis_db,
            synchronous_redis=self.sync_redis,
            subtensor=subtensor,
            metagraph=metagraph,
            wallet=wallet,
        )

    def set_mock_weights(self, uids: List[int], values: List[float]):
        weights_to_set = rdc.WeightsToSet(uids=uids, values=values, version_key=10000000000, netuid=self.config.netuid)
        self.sync_redis.rpush(rcst.WEIGHTS_TO_SET_QUEUE_KEY, json.dumps(weights_to_set.__dict__))

    async def test_poll_for_weights_then_set(self):
        test_uids = [0, 1, 2]
        test_values = [0.3, 0.2, 0.5]
        self.set_mock_weights(test_uids, test_values)

        # Mock the set_weights function
        mock_set_weights = MagicMock()

        # Mock the submit_extrinsic function
        mock_extrinsic = MagicMock()
        mock_extrinsic.process_events = MagicMock()
        mock_extrinsic.is_success = True

        # Patch both set_weights and submit_extrinsic
        with patch("validator.chain_node.src.set_weights.set_weights", mock_set_weights), patch.object(
            self.config.subtensor.substrate, "submit_extrinsic", return_value=mock_extrinsic
        ) as mock_submit:
            # Patch the continuous loop to run only once
            with patch(
                "validator.chain_node.src.set_weights.poll_for_weights_then_set", side_effect=[None, Exception("Stop")]
            ):
                with self.assertRaises(Exception):
                    await poll_for_weights_then_set(self.config)

            # Check if set_weights was called
            mock_set_weights.assert_called_once()

            # If set_weights was called, check if submit_extrinsic was called within it
            args, kwargs = mock_set_weights.call_args
            await set_weights(*args, **kwargs)

            mock_submit.assert_called()
            mock_extrinsic.process_events.assert_called()

        queue_length = await self.redis_db.llen(rcst.WEIGHTS_TO_SET_QUEUE_KEY)
        self.assertEqual(queue_length, 0, "Weights queue should be empty after processing")


if __name__ == "__main__":
    unittest.main()
