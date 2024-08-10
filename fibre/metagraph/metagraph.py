from abc import ABC, abstractmethod
import numpy as np
from numpy.typing import NDArray
import bittensor
from typing import List, Optional, Union, Tuple

from bittensor.chain_data import AxonInfo
from bittensor.utils.registration import torch




class MetagraphMixin(ABC):
    netuid: int
    network: str
    version: Union["torch.nn.Parameter", Tuple[NDArray]]
    n: Union["torch.nn.Parameter", NDArray]
    block: Union["torch.nn.Parameter", NDArray]
    stake: Union["torch.nn.Parameter", NDArray]
    total_stake: Union["torch.nn.Parameter", NDArray]
    ranks: Union["torch.nn.Parameter", NDArray]
    trust: Union["torch.nn.Parameter", NDArray]
    consensus: Union["torch.nn.Parameter", NDArray]
    validator_trust: Union["torch.nn.Parameter", NDArray]
    incentive: Union["torch.nn.Parameter", NDArray]
    emission: Union["torch.nn.Parameter", NDArray]
    dividends: Union["torch.nn.Parameter", NDArray]
    active: Union["torch.nn.Parameter", NDArray]
    last_update: Union["torch.nn.Parameter", NDArray]
    validator_permit: Union["torch.nn.Parameter", NDArray]
    weights: Union["torch.nn.Parameter", NDArray]
    bonds: Union["torch.nn.Parameter", NDArray]
    uids: Union["torch.nn.Parameter", NDArray]
    axons: List[AxonInfo]

    @abstractmethod
    def __init__(self, netuid: int, network: str = "finney", lite: bool = True, sync: bool = True):
        pass

    def sync(
        self,
        block: Optional[int] = None,
        lite: bool = True,
        subtensor: Optional["bittensor.subtensor"] = None,
    ):
        if not subtensor:
            subtensor = bittensor.subtensor(network=self.network)

        self._assign_neurons(block, lite, subtensor)

    def _assign_neurons(self, block, lite, subtensor: "bittensor.subtensor"):
        self.neurons = subtensor.neurons_lite(block=block, netuid=self.netuid)

    @staticmethod
    def _create_tensor(data, dtype) -> Union[NDArray, "torch.nn.Parameter"]:
        return np.array(data, dtype=dtype)


class NonTorchMetagraph(MetagraphMixin):
    def __init__(self, netuid: int, network: str = "finney", lite: bool = True, sync: bool = True):
        # super(metagraph, self).__init__()
        MetagraphMixin.__init__(self, netuid, network, lite, sync)

        self.netuid = netuid
        self.network = network
        self.version = (np.array([bittensor.__version_as_int__], dtype=np.int64),)
        self.n = np.array([0], dtype=np.int64)
        self.block = np.array([0], dtype=np.int64)
        self.stake = np.array([], dtype=np.float32)
        self.total_stake = np.array([], dtype=np.float32)
        self.ranks = np.array([], dtype=np.float32)
        self.trust = np.array([], dtype=np.float32)
        self.consensus = np.array([], dtype=np.float32)
        self.validator_trust = np.array([], dtype=np.float32)
        self.incentive = np.array([], dtype=np.float32)
        self.emission = np.array([], dtype=np.float32)
        self.dividends = np.array([], dtype=np.float32)
        self.active = np.array([], dtype=np.int64)
        self.last_update = np.array([], dtype=np.int64)
        self.validator_permit = np.array([], dtype=bool)
        self.weights = np.array([], dtype=np.float32)
        self.bonds = np.array([], dtype=np.int64)
        self.uids = np.array([], dtype=np.int64)
        self.axons: List[AxonInfo] = []
        if sync:
            self.sync(block=None, lite=lite)

    def _set_metagraph_attributes(self, block, subtensor):
        # TODO: Check and test the setting of each attribute
        self.n = self._create_tensor(len(self.neurons), dtype=np.int64)
        self.version = self._create_tensor([bittensor.__version_as_int__], dtype=np.int64)
        self.block = self._create_tensor(block if block else subtensor.block, dtype=np.int64)
        self.uids = self._create_tensor([neuron.uid for neuron in self.neurons], dtype=np.int64)
        self.trust = self._create_tensor([neuron.trust for neuron in self.neurons], dtype=np.float32)
        self.consensus = self._create_tensor([neuron.consensus for neuron in self.neurons], dtype=np.float32)
        self.incentive = self._create_tensor([neuron.incentive for neuron in self.neurons], dtype=np.float32)
        self.dividends = self._create_tensor([neuron.dividends for neuron in self.neurons], dtype=np.float32)
        self.ranks = self._create_tensor([neuron.rank for neuron in self.neurons], dtype=np.float32)
        self.emission = self._create_tensor([neuron.emission for neuron in self.neurons], dtype=np.float32)
        self.active = self._create_tensor([neuron.active for neuron in self.neurons], dtype=np.int64)
        self.last_update = self._create_tensor([neuron.last_update for neuron in self.neurons], dtype=np.int64)
        self.validator_permit = self._create_tensor([neuron.validator_permit for neuron in self.neurons], dtype=bool)
        self.validator_trust = self._create_tensor(
            [neuron.validator_trust for neuron in self.neurons], dtype=np.float32
        )
        self.total_stake = self._create_tensor([neuron.total_stake.tao for neuron in self.neurons], dtype=np.float32)
        self.stake = self._create_tensor([neuron.stake for neuron in self.neurons], dtype=np.float32)
        self.axons = [n.axon_info for n in self.neurons]


metagraph = NonTorchMetagraph
