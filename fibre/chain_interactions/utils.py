from scalecodec.base import RuntimeConfiguration
from scalecodec.type_registry import load_type_registry_preset
from fibre.chain_interactions import type_registry
from scalecodec import ScaleBytes, ScaleType


def create_scale_object(return_type: str, as_scale_bytes: ScaleBytes) -> ScaleType:
    rpc_runtime_config = RuntimeConfiguration()
    rpc_runtime_config.update_type_registry(load_type_registry_preset("legacy"))
    rpc_runtime_config.update_type_registry(type_registry.custom_rpc_type_registry)

    scale_object = rpc_runtime_config.create_scale_object(return_type, as_scale_bytes)
    return scale_object
