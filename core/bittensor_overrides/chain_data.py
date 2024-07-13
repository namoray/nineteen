import json
from dataclasses import dataclass, asdict
from core.logging import get_logger
from core.bittensor_overrides.utils import networking as net

logger = get_logger(__name__)


@dataclass
class AxonInfo:
    version: int
    ip: str
    port: int
    ip_type: int
    hotkey: str
    coldkey: str
    protocol: int = 4
    placeholder1: int = 0
    placeholder2: int = 0

    @property
    def is_serving(self) -> bool:
        """True if the endpoint is serving."""
        return self.ip != "0.0.0.0"

    def ip_str(self) -> str:
        """Return the whole IP as string"""
        return net.ip__str__(self.ip_type, self.ip, self.port)

    def __eq__(self, other: "AxonInfo"):
        if other is None:
            return False

        if (
            self.version == other.version
            and self.ip == other.ip
            and self.port == other.port
            and self.ip_type == other.ip_type
            and self.coldkey == other.coldkey
            and self.hotkey == other.hotkey
        ):
            return True

        return False

    def __str__(self):
        return "AxonInfo( {}, {}, {}, {} )".format(
            str(self.ip_str()), str(self.hotkey), str(self.coldkey), self.version
        )

    def __repr__(self):
        return self.__str__()

    def to_string(self) -> str:
        """Converts the AxonInfo object to a string representation using JSON."""
        try:
            return json.dumps(asdict(self))
        except (TypeError, ValueError) as e:
            logger.error(f"Error converting AxonInfo to string: {e}")
            return AxonInfo(0, "", 0, 0, "", "").to_string()

    @classmethod
    def from_string(cls, json_string: str) -> "AxonInfo":
        """
        Creates an AxonInfo object from its string representation using JSON.

        Args:
            json_string (str): The JSON string representation of the AxonInfo object.

        Returns:
            AxonInfo: An instance of AxonInfo created from the JSON string. If decoding fails, returns a default AxonInfo object with default values.

        Raises:
            json.JSONDecodeError: If there is an error in decoding the JSON string.
            TypeError: If there is a type error when creating the AxonInfo object.
            ValueError: If there is a value error when creating the AxonInfo object.
        """
        try:
            data = json.loads(json_string)
            return cls(**data)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}")
        except TypeError as e:
            logger.error(f"Type error: {e}")
        except ValueError as e:
            logger.error(f"Value error: {e}")
        return AxonInfo(0, "", 0, 0, "", "")

    @classmethod
    def from_neuron_info(cls, neuron_info: dict) -> "AxonInfo":
        """
        Converts a dictionary to an AxonInfo object.

        Args:
            neuron_info (dict): A dictionary containing the neuron information.

        Returns:
            instance (AxonInfo): An instance of AxonInfo created from the dictionary.
        """
        return cls(
            version=neuron_info["axon_info"]["version"],
            ip=net.int_to_ip(int(neuron_info["axon_info"]["ip"])),
            port=neuron_info["axon_info"]["port"],
            ip_type=neuron_info["axon_info"]["ip_type"],
            hotkey=neuron_info["hotkey"],
            coldkey=neuron_info["coldkey"],
        )
