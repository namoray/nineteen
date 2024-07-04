import asyncio
import threading
import time
import traceback
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar
import bittensor as bt

# import base miner class which takes care of most of the boilerplate
from config import configuration
from core import Task, constants as ccst, utils
from config.miner_config import config as miner_config
from core import bittensor_overrides as bto


T = TypeVar("T", bound=bt.Synapse)


metagraph = None

asyncio_lock: asyncio.Lock = asyncio.Lock()
threading_lock: threading.Lock = threading.Lock()
MIN_VALIDATOR_STAKE = 0 if miner_config.subtensor_network == "test" else 5000


class MinerRequestsStatus:
    def __init__(self) -> None:
        self.requests_from_each_validator = {}
        self._active_requests_for_each_concurrency_group: Dict[Task, int] = {}

    @property
    def active_requests_for_each_concurrency_group(self) -> Dict[Task, int]:
        return self._active_requests_for_each_concurrency_group

    def decrement_concurrency_group_from_task(self, task: Task) -> None:
        capacity_config = utils.load_capacities(miner_config.hotkey_name)
        concurrency_group_id = capacity_config.get(task.value, {}).get("concurrency_group_id")
        if concurrency_group_id is not None:
            concurrency_group_id = str(concurrency_group_id)
        current_number_of_concurrent_requests = self._active_requests_for_each_concurrency_group.get(
            concurrency_group_id, 1
        )
        self._active_requests_for_each_concurrency_group[concurrency_group_id] = (
            current_number_of_concurrent_requests - 1
        )


# Annoyingly needs to be global since we can't access the core miner with self in operations
# Code, as it needs to be static methods to attach the axon :/
miner_requests_stats = MinerRequestsStatus()


def base_blacklist(synapse: T) -> Tuple[bool, str]:
    if synapse.dendrite.hotkey not in metagraph.hotkeys:
        bt.logging.trace(f"Blacklisting unrecognized hotkey {synapse.dendrite.hotkey}")
        return True, synapse.dendrite.hotkey

    stake = metagraph.S[metagraph.hotkeys.index(synapse.dendrite.hotkey)]
    if stake < MIN_VALIDATOR_STAKE:
        bt.logging.trace(f"Blacklisting hotkey, stake too low! {synapse.dendrite.hotkey}")
        return True, synapse.dendrite.hotkey

    return False, synapse.dendrite.hotkey


def base_priority(synapse: T) -> float:
    """
    The priority function determines the order in which requests are handled.
    """

    return 1


class CoreMiner:
    def __init__(self) -> None:
        self.config = self.prepare_config_and_logging()
        self.wallet = bt.wallet(config=self.config)

        bt.logging.debug("Creating subtensor...")
        self.subtensor = bt.subtensor(config=self.config)

        global metagraph
        metagraph = self.subtensor.metagraph(netuid=self.config.netuid)

        if self.config.axon.external_ip is not None:
            bt.logging.debug(
                f"Will start axon on port {self.config.axon.port} and external ip {self.config.axon.external_ip}"
            )
            self.axon = bto.axon(
                wallet=self.wallet,
                port=self.config.axon.port,
                external_ip=self.config.axon.external_ip,
            )
        else:
            bt.logging.debug(f"Will start axon on port {self.config.axon.port}")
            self.axon = bto.axon(wallet=self.wallet, port=self.config.axon.port)

        self.should_exit: bool = False
        self.is_running: bool = False
        self.thread: Optional[threading.Thread] = None

    def run(self):
        self.validate_and_register_wallet()
        self.start_serving_axon()

        try:
            self.main_run_loop()

        except KeyboardInterrupt:
            self.handle_keyboard_interrupt()

        except Exception:
            bt.logging.error(traceback.format_exc())

    def prepare_config_and_logging(self) -> bt.config:
        base_config = configuration.get_miner_cli_config()
        bt.logging(config=base_config, logging_dir=base_config.full_path)
        return base_config

    def attach_to_axon(
        self,
        forward: Callable[[Any], bt.Synapse],
        blacklist: Callable[[Any], Tuple[bool, str]],
        priority: Callable[[Any], Any],
    ) -> None:
        self.axon.attach(forward_fn=forward, blacklist_fn=blacklist, priority_fn=priority)

    def validate_wallet_and_retrieve_uid(self) -> Optional[int]:
        if self.wallet.hotkey.ss58_address not in metagraph.hotkeys:
            bt.logging.error(
                f"Your miner / validator in the wallet: {self.wallet}, is not registered to this subnet on chain connection: {self.subtensor}. Run btcli register and try again."
            )
            exit()

        else:
            my_hotkey_uid: int = metagraph.hotkeys.index(self.wallet.hotkey.ss58_address)
            bt.logging.info(f"Running miner on uid: {my_hotkey_uid}")
            return my_hotkey_uid

    def validate_and_register_wallet(self) -> None:
        if not self.subtensor.is_hotkey_registered(
            netuid=self.config.netuid,
            hotkey_ss58=self.wallet.hotkey.ss58_address,
        ):
            bt.logging.error(
                f"Wallet: {self.wallet} is not registered on netuid {self.config.netuid} on the network {self.config.subtensor.chain_endpoint}"
                f". Please register the hotkey using `btcli s register --netuid 19` before trying again"
            )
            exit()

    def start_serving_axon(self) -> None:
        bt.logging.info(
            f"Serving axon on network: {self.config.subtensor.chain_endpoint} with netuid: {self.config.netuid}"
        )
        self.axon.serve(netuid=self.config.netuid, subtensor=self.subtensor)
        bt.logging.info(f"Starting axon server on port: {self.config.axon.port}")
        self.axon.start()

    def main_run_loop(self) -> None:
        self.last_epoch_block = self.subtensor.get_current_block()
        bt.logging.info("Miner started up - lets go! 🚀🚀")
        step = 0

        while not self.should_exit:
            self.wait_for_next_epoch()

            bt.logging.debug("Resyncing metagraph...")
            global metagraph

            metagraph = self.subtensor.metagraph(
                netuid=self.config.netuid,
                lite=True,
                block=self.last_epoch_block,
            )

            step += 1

    def wait_for_next_epoch(self) -> None:
        current_block = self.subtensor.get_current_block()
        while current_block - self.last_epoch_block < ccst.BLOCKS_PER_EPOCH:
            if self.should_exit:
                break
            time.sleep(1)
            current_block = self.subtensor.get_current_block()
        self.last_epoch_block = self.subtensor.get_current_block()
        global requests_from_each_validator
        requests_from_each_validator = {}

    def handle_keyboard_interrupt(self) -> None:
        self.axon.stop()
        bt.logging.success("Miner killed by keyboard interrupt.")
        exit()

    def run_in_background_thread(self) -> None:
        if not self.is_running:
            bt.logging.debug("Starting miner in background thread.")
            self.should_exit = False

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            self.is_running = True

            bt.logging.debug("Started")

    def stop_run_thread(self) -> None:
        if self.thread is None:
            raise Exception("Oh no!")

        if self.is_running:
            bt.logging.debug("Stopping miner in background thread.")
            self.should_exit = True
            self.thread.join(5)
            self.is_running = False
            bt.logging.debug("Stopped")

    def __enter__(self):
        self.run_in_background_thread()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_run_thread()
