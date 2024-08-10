from enum import Enum
from pydantic import BaseModel

from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Union

from scalecodec.utils.ss58 import ss58_encode
from scalecodec import ScaleBytes
from fibre.chain_interactions.interface import create_scale_object
from fibre import constants as fcst

U16_MAX = 65535
RAOPERTAO = 1e9


def U16_NORMALIZED_FLOAT(x: int) -> float:
    return float(x) / float(U16_MAX)


class Balance:
    """
    Represents the bittensor balance of the wallet, stored as rao (int).
    This class provides a way to interact with balances in two different units: rao and tao.
    It provides methods to convert between these units, as well as to perform arithmetic and comparison operations.

    Attributes:
        unit: A string representing the symbol for the tao unit.
        rao_unit: A string representing the symbol for the rao unit.
        rao: An integer that stores the balance in rao units.
        tao: A float property that gives the balance in tao units.
    """

    unit: str = fcst.TAO_SYMBOL
    rao_unit: str = fcst.RAO_SYMBOL
    rao: int
    tao: float

    def __init__(self, balance: Union[int, float]):
        """
        Initialize a Balance object. If balance is an int, it's assumed to be in rao.
        If balance is a float, it's assumed to be in tao.

        Args:
            balance: The initial balance, in either rao (if an int) or tao (if a float).
        """
        if isinstance(balance, int):
            self.rao = balance
        elif isinstance(balance, float):
            # Assume tao value for the float
            self.rao = int(balance * pow(10, 9))
        else:
            raise TypeError("balance must be an int (rao) or a float (tao)")

    @property
    def tao(self):
        return self.rao / pow(10, 9)

    def __int__(self):
        return self.rao

    def __float__(self):
        return self.tao

    def __str__(self):
        return f"{self.unit}{float(self.tao):,.9f}"

    def __rich__(self):
        return "[green]{}[/green][green]{}[/green][green].[/green][dim green]{}[/dim green]".format(
            self.unit,
            format(float(self.tao), "f").split(".")[0],
            format(float(self.tao), "f").split(".")[1],
        )

    def __str_rao__(self):
        return f"{self.rao_unit}{int(self.rao)}"

    def __rich_rao__(self):
        return f"[green]{self.rao_unit}{int(self.rao)}[/green]"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other: Union[int, float, "Balance"]):
        if other is None:
            return False

        if hasattr(other, "rao"):
            return self.rao == other.rao
        else:
            try:
                # Attempt to cast to int from rao
                other_rao = int(other)
                return self.rao == other_rao
            except (TypeError, ValueError):
                raise NotImplementedError("Unsupported type")

    def __ne__(self, other: Union[int, float, "Balance"]):
        return not self == other

    def __gt__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "rao"):
            return self.rao > other.rao
        else:
            try:
                # Attempt to cast to int from rao
                other_rao = int(other)
                return self.rao > other_rao
            except ValueError:
                raise NotImplementedError("Unsupported type")

    def __lt__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "rao"):
            return self.rao < other.rao
        else:
            try:
                # Attempt to cast to int from rao
                other_rao = int(other)
                return self.rao < other_rao
            except ValueError:
                raise NotImplementedError("Unsupported type")

    def __le__(self, other: Union[int, float, "Balance"]):
        try:
            return self < other or self == other
        except TypeError:
            raise NotImplementedError("Unsupported type")

    def __ge__(self, other: Union[int, float, "Balance"]):
        try:
            return self > other or self == other
        except TypeError:
            raise NotImplementedError("Unsupported type")

    def __add__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "rao"):
            return Balance.from_rao(int(self.rao + other.rao))
        else:
            try:
                # Attempt to cast to int from rao
                return Balance.from_rao(int(self.rao + other))
            except (ValueError, TypeError):
                raise NotImplementedError("Unsupported type")

    def __radd__(self, other: Union[int, float, "Balance"]):
        try:
            return self + other
        except TypeError:
            raise NotImplementedError("Unsupported type")

    def __sub__(self, other: Union[int, float, "Balance"]):
        try:
            return self + -other
        except TypeError:
            raise NotImplementedError("Unsupported type")

    def __rsub__(self, other: Union[int, float, "Balance"]):
        try:
            return -self + other
        except TypeError:
            raise NotImplementedError("Unsupported type")

    def __mul__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "rao"):
            return Balance.from_rao(int(self.rao * other.rao))
        else:
            try:
                # Attempt to cast to int from rao
                return Balance.from_rao(int(self.rao * other))
            except (ValueError, TypeError):
                raise NotImplementedError("Unsupported type")

    def __rmul__(self, other: Union[int, float, "Balance"]):
        return self * other

    def __truediv__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "rao"):
            return Balance.from_rao(int(self.rao / other.rao))
        else:
            try:
                # Attempt to cast to int from rao
                return Balance.from_rao(int(self.rao / other))
            except (ValueError, TypeError):
                raise NotImplementedError("Unsupported type")

    def __rtruediv__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "rao"):
            return Balance.from_rao(int(other.rao / self.rao))
        else:
            try:
                # Attempt to cast to int from rao
                return Balance.from_rao(int(other / self.rao))
            except (ValueError, TypeError):
                raise NotImplementedError("Unsupported type")

    def __floordiv__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "rao"):
            return Balance.from_rao(int(self.tao // other.tao))
        else:
            try:
                # Attempt to cast to int from rao
                return Balance.from_rao(int(self.rao // other))
            except (ValueError, TypeError):
                raise NotImplementedError("Unsupported type")

    def __rfloordiv__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "rao"):
            return Balance.from_rao(int(other.rao // self.rao))
        else:
            try:
                # Attempt to cast to int from rao
                return Balance.from_rao(int(other // self.rao))
            except (ValueError, TypeError):
                raise NotImplementedError("Unsupported type")

    def __nonzero__(self) -> bool:
        return bool(self.rao)

    def __neg__(self):
        return Balance.from_rao(-self.rao)

    def __pos__(self):
        return Balance.from_rao(self.rao)

    def __abs__(self):
        return Balance.from_rao(abs(self.rao))

    @staticmethod
    def from_float(amount: float):
        rao = int(amount * pow(10, 9))
        return Balance(rao)

    @staticmethod
    def from_tao(amount: float):
        rao = int(amount * pow(10, 9))
        return Balance(rao)

    @staticmethod
    def from_rao(amount: int):
        return Balance(amount)


class Node(BaseModel):
    version: int
    hotkey: str
    coldkey: str
    axon_uid: int
    incentive: float
    netuid: int
    stake: float
    ip: str
    ip_type: int
    port: int
    protocol: int = 4


class ChainDataType(Enum):
    NeuronInfo = 1
    SubnetInfo = 2
    DelegateInfo = 3
    NeuronInfoLite = 4
    DelegatedInfo = 5
    StakeInfo = 6
    IPInfo = 7
    SubnetHyperparameters = 8
    ScheduledColdkeySwapInfo = 9


def from_scale_encoding_using_type_string(
    input_: Union[List[int], bytes, ScaleBytes], type_string: str
) -> Optional[Dict]:
    if isinstance(input_, ScaleBytes):
        as_scale_bytes = input_
    else:
        if isinstance(input_, list) and all([isinstance(i, int) for i in input_]):
            vec_u8 = input_
            as_bytes = bytes(vec_u8)
        elif isinstance(input_, bytes):
            as_bytes = input_
        else:
            raise TypeError("input_ must be a List[int], bytes, or ScaleBytes")

        as_scale_bytes = ScaleBytes(as_bytes)

    scale_object = create_scale_object(type_string, as_scale_bytes)

    return scale_object.decode()


def from_scale_encoding(
    input_: Union[List[int], bytes, ScaleBytes],
    type_name: ChainDataType,
    is_vec: bool = False,
    is_option: bool = False,
) -> Optional[Dict]:
    """
    Decodes input_ data from SCALE encoding based on the specified type name and modifiers.

    Args:
        input_ (Union[List[int], bytes, ScaleBytes]): The input_ data to decode.
        type_name (ChainDataType): The type of data being decoded.
        is_vec (bool, optional): Whether the data is a vector of the specified type. Default is ``False``.
        is_option (bool, optional): Whether the data is an optional value of the specified type. Default is ``False``.

    Returns:
        Optional[Dict]: The decoded data as a dictionary, or ``None`` if the decoding fails.
    """
    type_string = type_name.name
    if type_name == ChainDataType.DelegatedInfo:
        # DelegatedInfo is a tuple of (DelegateInfo, Compact<u64>)
        type_string = f"({ChainDataType.DelegateInfo.name}, Compact<u64>)"
    if is_option:
        type_string = f"Option<{type_string}>"
    if is_vec:
        type_string = f"Vec<{type_string}>"

    return from_scale_encoding_using_type_string(input_, type_string)


@dataclass
class NeuronInfoLite:
    """Dataclass for neuron metadata, but without the weights and bonds."""

    hotkey: str
    coldkey: str
    uid: int
    netuid: int
    active: int
    stake: Balance
    # mapping of coldkey to amount staked to this Neuron
    stake_dict: Dict[str, Balance]
    total_stake: Balance
    rank: float
    emission: float
    incentive: float
    consensus: float
    trust: float
    validator_trust: float
    dividends: float
    last_update: int
    validator_permit: bool
    pruning_score: int
    is_null: bool = False

    @classmethod
    def fix_decoded_values(cls, neuron_info_decoded: Any) -> "NeuronInfoLite":
        """Fixes the values of the NeuronInfoLite object."""
        neuron_info_decoded["hotkey"] = ss58_encode(neuron_info_decoded["hotkey"], fcst.SS58_FORMAT)
        neuron_info_decoded["coldkey"] = ss58_encode(neuron_info_decoded["coldkey"], fcst.SS58_FORMAT)
        stake_dict = {
            ss58_encode(coldkey, fcst.SS58_FORMAT): Balance.from_rao(int(stake))
            for coldkey, stake in neuron_info_decoded["stake"]
        }
        neuron_info_decoded["stake_dict"] = stake_dict
        neuron_info_decoded["stake"] = sum(stake_dict.values())
        neuron_info_decoded["total_stake"] = neuron_info_decoded["stake"]
        neuron_info_decoded["rank"] = U16_NORMALIZED_FLOAT(neuron_info_decoded["rank"])
        neuron_info_decoded["emission"] = neuron_info_decoded["emission"] / RAOPERTAO
        neuron_info_decoded["incentive"] = U16_NORMALIZED_FLOAT(neuron_info_decoded["incentive"])
        neuron_info_decoded["consensus"] = U16_NORMALIZED_FLOAT(neuron_info_decoded["consensus"])
        neuron_info_decoded["trust"] = U16_NORMALIZED_FLOAT(neuron_info_decoded["trust"])
        neuron_info_decoded["validator_trust"] = U16_NORMALIZED_FLOAT(neuron_info_decoded["validator_trust"])
        neuron_info_decoded["dividends"] = U16_NORMALIZED_FLOAT(neuron_info_decoded["dividends"])

        return cls(**neuron_info_decoded)

    @classmethod
    def from_vec_u8(cls, vec_u8: List[int]) -> "NeuronInfoLite":
        """Returns a NeuronInfoLite object from a ``vec_u8``."""
        if len(vec_u8) == 0:
            return NeuronInfoLite.get_null_neuron()

        decoded = from_scale_encoding(vec_u8, ChainDataType.NeuronInfoLite)
        if decoded is None:
            return NeuronInfoLite.get_null_neuron()

        return NeuronInfoLite.fix_decoded_values(decoded)

    @classmethod
    def list_from_vec_u8(cls, vec_u8: List[int]) -> List["NeuronInfoLite"]:
        """Returns a list of NeuronInfoLite objects from a ``vec_u8``."""

        decoded_list = from_scale_encoding(vec_u8, ChainDataType.NeuronInfoLite, is_vec=True)
        if decoded_list is None:
            return []

        decoded_list = [NeuronInfoLite.fix_decoded_values(decoded) for decoded in decoded_list]
        return decoded_list

    @staticmethod
    def get_null_neuron() -> "NeuronInfoLite":
        neuron = NeuronInfoLite(
            uid=0,
            netuid=0,
            active=0,
            stake=Balance.from_rao(0),
            stake_dict={},
            total_stake=Balance.from_rao(0),
            rank=0,
            emission=0,
            incentive=0,
            consensus=0,
            trust=0,
            validator_trust=0,
            dividends=0,
            last_update=0,
            validator_permit=False,
            prometheus_info=None,
            axon_info=None,
            is_null=True,
            coldkey="000000000000000000000000000000000000000000000000",
            hotkey="000000000000000000000000000000000000000000000000",
            pruning_score=0,
        )
        return neuron
