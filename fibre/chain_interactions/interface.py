from typing import Any, TypedDict
from substrateinterface import SubstrateInterface
from fibre.chain_interactions import type_registry
import scalecodec

from tenacity import retry, stop_after_attempt, wait_exponential

from fibre.chain_interactions.models import Node
from fibre.chain_interactions import models
from fibre.chain_interactions import utils as chain_utils


class ParamWithTypes(TypedDict):
    name: str
    type: str  # ScaleType string of the parameter.


class ChainInterface:
    def __init__(self, netuid: int, chain_endpoint: str = "wss://entrypoint-finney.opentensor.ai:443"):
        self.type_registry = type_registry.type_registry
        self.substrate = SubstrateInterface(
            ss58_format=42, use_remote_preset=True, url=chain_endpoint, type_registry=self.type_registry
        )
        self.nodes: list[Node] = []

    def _encode_params(
        self,
        call_definition: list[ParamWithTypes],
        params: list[Any] | dict[str, Any],
    ) -> str:
        """Returns a hex encoded string of the params using their types."""
        param_data = scalecodec.ScaleBytes(b"")

        for i, param in enumerate(call_definition["params"]):  # type: ignore
            scale_obj = self.substrate.create_scale_object(param["type"])
            if isinstance(params, list):
                param_data += scale_obj.encode(params[i])
            else:
                if param["name"] not in params:
                    raise ValueError(f"Missing param {param['name']} in params dict.")

                param_data += scale_obj.encode(params[param["name"]])

        return param_data.to_hex()

    def _state_call(
        self,
        method: str,
        data: str,
        block: int | None = None,
    ) -> dict[str, Any]:
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=4),
            reraise=True,
        )
        def make_substrate_call() -> dict[str, Any]:
            block_hash = None if block is None else self.substrate.get_block_hash(block)
            params = [method, data, block_hash] if block_hash else [method, data]

            return self.substrate.rpc_request(
                method="state_call",
                params=params,
            )

        return make_substrate_call()

    def _query_runtime_api(
        self,
        runtime_api: str,
        method: str,
        params: list[int] | dict[str, int] | None,
        block: int | None = None,
    ) -> str | None:
        call_definition = self.type_registry["runtime_api"][runtime_api]["methods"][method]

        json_result = self._state_call(
            method=f"{runtime_api}_{method}",
            data=("0x" if params is None else self._encode_params(call_definition=call_definition, params=params)),
            block=block,
        )

        if json_result is None:
            return None

        return_type = call_definition["type"]

        as_scale_bytes = scalecodec.ScaleBytes(json_result["result"])

        scale_object = chain_utils.create_scale_object(return_type, as_scale_bytes)

        if scale_object.data.to_hex() == "0x0400":
            return None

        return scale_object.decode()

    def neurons_lite(self, netuid: int, block: int | None = None) -> list[models.NeuronInfoLite]:
        hex_bytes_result = self._query_runtime_api(
            runtime_api="NeuronInfoRuntimeApi",
            method="get_neurons_lite",
            params=[netuid],
            block=block,
        )

        if hex_bytes_result is None:
            return []

        if hex_bytes_result.startswith("0x"):
            bytes_result = bytes.fromhex(hex_bytes_result[2:])
        else:
            bytes_result = bytes.fromhex(hex_bytes_result)

        return models.NeuronInfoLite.list_from_vec_u8(bytes_result)  # type: ignore
