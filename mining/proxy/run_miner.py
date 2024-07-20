import importlib
import time
import tracemalloc

from core import bittensor_overrides as bt
from core import utils, Task
from mining.proxy import core_miner
from config.miner_config import config
from mining.proxy import operations
# For determinism

tracemalloc.start()

if __name__ == "__main__":
    miner = core_miner.CoreMiner()

    bt.logging.info("Loading all config & resources....")

    if config.debug_miner:
        bt.logging.debug("Miner is in debug mode 🪳🔫")

    capacity_module = importlib.import_module("operations.capacity_operation")
    capacity_operation_name = capacity_module.operation_name

    CapcityClass = getattr(capacity_module, capacity_operation_name)
    miner.attach_to_axon(CapcityClass.forward, CapcityClass.blacklist, CapcityClass.priority)

    task_and_capacities = utils.load_capacities(hotkey=config.hotkey_name)
    operations_supported = set()
    if not config.debug_miner:
        for task in Task:
            operation_module = operations.TASKS_TO_MINER_OPERATION_MODULES[task]
            if operation_module.__name__ not in operations_supported:
                operations_supported.add(operation_module.__name__)
                operation_class = getattr(operation_module, operation_module.operation_name)
                miner.attach_to_axon(
                    getattr(operation_class, "forward"),
                    getattr(operation_class, "blacklist"),
                    getattr(operation_class, "priority"),
                )

    with miner as running_miner:
        while True:
            time.sleep(240)
