import asyncio
import hashlib
from typing import Callable, Dict

from mining.db.db_management import miner_db_manager


# Would people want this to be in a DB instead which is read on every request, but then more configurable?
def load_concurrency_groups(hotkey: str) -> Dict[str, float]:
    return miner_db_manager.load_concurrency_groups()


def load_capacities(hotkey: str) -> Dict[str, Dict[str, float]]:
    return miner_db_manager.load_task_capacities(hotkey)


def start_async_loop(func: Callable, *args, **kwargs):
    """Start the event loop and run the async tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(func(*args, **kwargs))

def hash(content, encoding="utf-8"):
    sha3 = hashlib.sha3_256()

    # Update the hash object with the concatenated string
    sha3.update(content.encode(encoding))

    # Produce the hash
    return sha3.hexdigest()