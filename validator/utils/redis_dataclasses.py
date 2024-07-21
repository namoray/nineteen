from dataclasses import dataclass


@dataclass
class PublicKeypairInfo:
    ss58_address: str
    ss58_format: int
    crypto_type: str
    public_key: str


@dataclass
class WeightsToSet:
    uids: list[int]
    values: list[float]
    version_key: int
