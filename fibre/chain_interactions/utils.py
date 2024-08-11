from scalecodec.base import RuntimeConfiguration
from scalecodec.type_registry import load_type_registry_preset
from fibre.chain_interactions import type_registry
from scalecodec import ScaleBytes, ScaleType


from fibre.chain_interactions import utils as chain_utils
from fibre.chain_interactions.models import ChainDataType


def create_scale_object_from_scale_bytes(return_type: str, as_scale_bytes: ScaleBytes) -> ScaleType:
    rpc_runtime_config = RuntimeConfiguration()
    rpc_runtime_config.update_type_registry(load_type_registry_preset("legacy"))
    rpc_runtime_config.update_type_registry(type_registry.custom_rpc_type_registry)
    scale_object = rpc_runtime_config.create_scale_object(return_type, as_scale_bytes)
    return scale_object


def create_scale_object_from_scale_encoding(
    input_: list[int] | bytes | ScaleBytes,
    type_name: ChainDataType,
    is_vec: bool = False,
    is_option: bool = False,
) -> dict | None:
    type_string = type_name.name
    if type_name == ChainDataType.DelegatedInfo:
        type_string = f"({ChainDataType.DelegateInfo.name}, Compact<u64>)"
    if is_option:
        type_string = f"Option<{type_string}>"
    if is_vec:
        type_string = f"Vec<{type_string}>"

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

    scale_object = chain_utils.create_scale_object_from_scale_bytes(type_string, as_scale_bytes)

    return scale_object.decode()
