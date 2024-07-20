from typing import Dict
from mining.db.db_management import miner_db_manager


# Would people want this to be in a DB instead which is read on every request, but then more configurable?
def load_concurrency_groups(hotkey: str) -> Dict[str, float]:
    return miner_db_manager.load_concurrency_groups()


def load_capacities(hotkey: str) -> Dict[str, Dict[str, float]]:
    return miner_db_manager.load_task_capacities(hotkey)
