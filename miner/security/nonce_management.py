import threading
import time
from typing import Iterator


class NonceManager:
    def __init__(self) -> None:
        self._nonces: dict[str, float] = {}
        self.TTL: int = 60
        self._lock: threading.Lock = threading.Lock()
        self._running: bool = True
        self._cleanup_thread: threading.Thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self._cleanup_thread.start()

    def add_nonce(self, nonce: str) -> None:
        self._nonces[nonce] = time.time() + self.TTL

    def nonce_in_nonces(self, nonce: str) -> bool:
        with self._lock:
            expiry_time = self._nonces.get(nonce)
            if expiry_time is None:
                self.add_nonce(nonce)
                return False
            else:
                current_time = time.time()
                self._nonces[nonce] = current_time + self.TTL
                return True

    def cleanup(self) -> None:
        with self._lock:
            current_time = time.time()
            expired_nonces: list[str] = [
                nonce for nonce, expiry_time in self._nonces.items() if current_time > expiry_time
            ]
            for nonce in expired_nonces:
                del self._nonces[nonce]

    def _periodic_cleanup(self) -> None:
        while self._running:
            time.sleep(65)  # Sleep for 65 seconds (1 minute + 5 seconds)
            self.cleanup()

    def __contains__(self, nonce: str) -> bool:
        return self.nonce_in_nonces(nonce)

    def __len__(self) -> int:
        return len(self._nonces)

    def __iter__(self) -> Iterator[str]:
        return iter(self._nonces.keys())

    def shutdown(self) -> None:
        self._running = False
        self._cleanup_thread.join()
