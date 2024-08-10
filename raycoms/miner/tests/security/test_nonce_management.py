import unittest
from unittest.mock import patch
from raycoms.miner.security.nonce_management import NonceManager


class TestNonceManager(unittest.TestCase):
    def setUp(self):
        self.nonce_manager = NonceManager()

    def test_add_nonce(self):
        nonce = "test_nonce"
        self.nonce_manager.add_nonce(nonce)
        self.assertIn(nonce, self.nonce_manager._nonces)

    def test_nonce_in_nonces_new_nonce(self):
        nonce = "new_nonce"
        result = self.nonce_manager.nonce_in_nonces(nonce)
        self.assertFalse(result)
        self.assertIn(nonce, self.nonce_manager._nonces)

    def test_nonce_in_nonces_existing_nonce(self):
        nonce = "existing_nonce"
        self.nonce_manager.add_nonce(nonce)
        result = self.nonce_manager.nonce_in_nonces(nonce)
        self.assertTrue(result)

    @patch("time.time")
    def test_cleanup_expired_nonces(self, mock_time):
        mock_time.return_value = 100
        self.nonce_manager.add_nonce("expired_nonce")
        mock_time.return_value = 200
        self.nonce_manager.add_nonce("valid_nonce")

        self.nonce_manager.cleanup_expired_nonces()

        self.assertNotIn("expired_nonce", self.nonce_manager._nonces)
        self.assertIn("valid_nonce", self.nonce_manager._nonces)

    def test_contains(self):
        nonce = "test_nonce"
        self.nonce_manager.add_nonce(nonce)
        self.assertIn(nonce, self.nonce_manager)

    def test_len(self):
        self.nonce_manager.add_nonce("nonce1")
        self.nonce_manager.add_nonce("nonce2")
        self.assertEqual(len(self.nonce_manager), 2)

    def test_iter(self):
        nonces = ["nonce1", "nonce2", "nonce3"]
        for nonce in nonces:
            self.nonce_manager.add_nonce(nonce)

        self.assertEqual(set(self.nonce_manager), set(nonces))

    @patch("threading.Thread")
    def test_shutdown(self, mock_thread):
        mock_thread_instance = mock_thread.return_value
        self.nonce_manager._cleanup_thread = mock_thread_instance
        self.nonce_manager._running = True

        self.nonce_manager.shutdown()

        self.assertFalse(self.nonce_manager._running)
        mock_thread_instance.join.assert_called_once()


if __name__ == "__main__":
    unittest.main()
