from abc import ABC
from abc import abstractmethod
from typing import Awaitable
from typing import Callable

from aiohttp import ClientResponse
from pydantic import BaseModel
from starlette.responses import StreamingResponse as _StreamingResponse
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send

from core import bittensor_overrides as bt


class BTStreamingResponseModel(BaseModel):
    token_streamer: Callable[[Send], Awaitable[None]]


class StreamingSynapse(bt.Synapse, ABC):
    class Config:
        validate_assignment = True

    class BTStreamingResponse(_StreamingResponse):
        def __init__(self, model: BTStreamingResponseModel, **kwargs):
            super().__init__(content=iter(()), **kwargs)
            self.token_streamer = model.token_streamer

        async def stream_response(self, send: Send):
            headers = [(b"content-type", b"text/event-stream")] + self.raw_headers

            await send({"type": "http.response.start", "status": 200, "headers": headers})

            await self.token_streamer(send)

            await send({"type": "http.response.body", "body": b"", "more_body": False})

        async def __call__(self, scope: Scope, receive: Receive, send: Send):
            await self.stream_response(send)

    @abstractmethod
    async def process_streaming_response(self, response: ClientResponse):
        ...

    @abstractmethod
    def extract_response_json(self, response: ClientResponse) -> dict:
        ...

    def create_streaming_response(self, token_streamer: Callable[[Send], Awaitable[None]]) -> BTStreamingResponse:
        model_instance = BTStreamingResponseModel(token_streamer=token_streamer)

        return self.BTStreamingResponse(model_instance)
