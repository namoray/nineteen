from typing import Dict, List, Optional
from core.tasks import Task
from core import bittensor_overrides as bt

from models import base_models

from typing import AsyncIterator

from starlette.responses import StreamingResponse


class Capacity(bt.Synapse, base_models.CapacityBase):
    def deserialize(self) -> dict[Task | str, base_models.CapacityForTask]:
        return self.capacities


class TextToImage(bt.Synapse, base_models.TextToImageBase):
    def deserialize(self) -> Optional[List[str]]:
        return self.image_b64


class ImageToImage(bt.Synapse, base_models.ImageToImageBase):
    def deserialize(self) -> Optional[List[str]]:
        return self.image_b64


class Inpaint(bt.Synapse, base_models.InpaintBase):
    def deserialize(self) -> Optional[List[str]]:
        return self.image_b64


class Avatar(bt.Synapse, base_models.AvatarBase):
    def deserialize(self) -> Optional[List[str]]:
        return self.image_b64


# class Scribble(bt.Synapse, base_models.ScribbleBase):
#     def deserialize(self) -> Optional[List[str]]:
#         return self.image_b64


class Upscale(bt.Synapse, base_models.UpscaleBase):
    def deserialize(self) -> Optional[List[str]]:
        return self.image_b64


class ClipEmbeddings(bt.Synapse, base_models.ClipEmbeddingsBase):
    def deserialize(self) -> Optional[List[List[float]]]:
        return self.clip_embeddings


class Chat(bt.StreamingSynapse, base_models.ChatBase):
    def deserialize(self) -> Optional[Dict[str, str]]:
        return None

    async def process_streaming_response(self, response: StreamingResponse) -> AsyncIterator[str]:
        async for chunk in response.content.iter_any():
            if isinstance(chunk, bytes):
                tokens = chunk.decode("utf-8")
                yield tokens

    def extract_response_json(self, response) -> dict:
        """
        Abstract method that must be implemented by the subclass.
        This method should provide logic to extract JSON data from the response, including headers and content.
        It is called after the response has been processed and is responsible for retrieving structured data
        that can be used by the application.

        Args:
            response: The response object from which to extract JSON data.
        """
        headers = {k.decode("utf-8"): v.decode("utf-8") for k, v in response.__dict__["_raw_headers"]}

        def extract_info(prefix: str) -> dict[str, str]:
            return {key.split("_")[-1]: value for key, value in headers.items() if key.startswith(prefix)}

        return {
            "name": headers.get("name", ""),
            "timeout": float(headers.get("timeout", 0)),
            "total_size": int(headers.get("total_size", 0)),
            "header_size": int(headers.get("header_size", 0)),
            "dendrite": extract_info("bt_header_dendrite"),
            "axon": extract_info("bt_header_axon"),
        }
