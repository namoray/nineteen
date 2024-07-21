import asyncio
import json
import time
from typing import Any, AsyncGenerator, Union
import uuid

import aiohttp
from redis.asyncio import Redis
from core import bittensor_overrides as bt
from core.logging import get_logger
from dataclasses import dataclass
import base64

logger = get_logger(__name__)

### NOTE: This is repeated throughout, how to better organise?
SIGNING_WEIGHTS_QUEUE_KEY = "SIGNING_WEIGHTS_QUEUE"
SIGNED_MESSAGES_KEY = "SIGNED_MESSAGES"


@dataclass
class SigningPayload:
    message: bytes | str
    job_id: str
    is_b64encoded: bool

    def to_dict(self):
        if isinstance(self.message, bytes):
            return {
                "message": base64.b64encode(self.message).decode("utf-8"),
                "job_id": self.job_id,
                "is_b64encoded": True,
            }
        elif isinstance(self.message, str):
            return {"message": self.message, "job_id": self.job_id, "is_b64encoded": False}
        else:
            raise TypeError("message must be either bytes or str")

    @classmethod
    def from_dict(cls, data):
        is_b64encoded = data["is_b64encoded"]
        message = data["message"]
        if is_b64encoded:
            message = base64.b64decode(message)
        return cls(message=message, job_id=data["job_id"], is_b64encoded=is_b64encoded)


@dataclass
class SignedPayload:
    signature: str
    job_id: str


def _construct_signed_message_key(job_id: str) -> str:
    return f"{SIGNED_MESSAGES_KEY}:{job_id}"


### END OF NOTE


class dendrite:
    def __init__(self, redis_db: Redis) -> None:
        # Unique identifier for the instance
        self.uuid = str(uuid.uuid1())

        self.synapse_history: list = []

        self._session: aiohttp.ClientSession | None = None
        self.redis_db = redis_db

    @property
    async def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _sign_mesage(self, message: str) -> str:
        job_id = str(uuid.uuid4())
        await self.redis_db.rpush(
            SIGNING_WEIGHTS_QUEUE_KEY,
            json.dumps(SigningPayload(message=message, job_id=job_id, is_b64encoded=False).to_dict()),
        )

        job_results_key = _construct_signed_message_key(job_id)

        _, payload_raw = await self.redis_db.blpop(job_results_key, 10)

        payload = SignedPayload(**json.loads(payload_raw))

        return payload.signature

    def _log_outgoing_request(self, synapse: bt.Synapse):
        logger.info(
            f"dendrite | --> | {synapse.get_total_size()} B | {synapse.name} | {synapse.axon.hotkey} | {synapse.axon.ip}:{str(synapse.axon.port)} | 0 | Success"
        )

    def _log_incoming_response(self, synapse: bt.Synapse):
        logger.info(
            f"dendrite | <-- | {synapse.get_total_size()} B | {synapse.name} | {synapse.axon.hotkey} | {synapse.axon.ip}:{str(synapse.axon.port)} | {synapse.dendrite.status_code} | {synapse.dendrite.status_message}"
        )

    async def aclose_session(self):
        if self._session:
            await self._session.close()
            self._session = None

    def _get_endpoint_url(self, target_axon: bt.axon, request_name: str) -> str:
        endpoint = f"{target_axon.ip}:{str(target_axon.port)}"

        # TODO: COMMENT OUT FOR MAINNET
        # external_ip = networking.int_to_ip(self.external_ip)
        # endpoint = (
        #     f"0.0.0.0:{str(target_axon.port)}"
        #     if target_axon.ip == str(external_ip)
        #     else f"{target_axon.ip}:{str(target_axon.port)}"
        # )

        return f"http://{endpoint}/{request_name}"

    def _handle_request_errors(
        self,
        synapse: bt.Synapse,
        request_name: str,
        exception: Exception,
        connection_timeout: float,
        response_timeout: float,
    ) -> None:
        if isinstance(exception, aiohttp.ClientConnectorError):
            synapse.dendrite.status_code = "503"
            synapse.dendrite.status_message = (
                f"Service at {synapse.axon.ip}:{str(synapse.axon.port)}/{request_name} unavailable."
            )
        elif isinstance(exception, asyncio.TimeoutError):
            if "Connection timeout" in str(exception):
                synapse.dendrite.status_code = "408"
                synapse.dendrite.status_message = f"Initial connection timeout after {connection_timeout} seconds."
            else:
                synapse.dendrite.status_code = "408"
                synapse.dendrite.status_message = f"Response timeout after {response_timeout} seconds."
        else:
            synapse.dendrite.status_code = "422"
            synapse.dendrite.status_message = f"Failed to parse response object with error: {str(exception)}"

    async def call_stream(
        self,
        target_axon: Union[bt.AxonInfo, bt.axon],
        synapse: bt.StreamingSynapse,
        connect_timeout: float = 2.0,
        response_timeout: float = 3.0,
        deserialize: bool = True,
        log_requests_and_responses: bool = True,
    ) -> AsyncGenerator[Any, Any]:
        """
        Sends a request to a specified Axon and yields streaming responses.

        Similar to `call`, but designed for scenarios where the Axon sends back data in
        multiple chunks or streams. The function yields each chunk as it is received. This is
        useful for processing large responses piece by piece without waiting for the entire
        data to be transmitted.

        """

        # Record start time
        start_time = time.time()
        target_axon = target_axon.info() if isinstance(target_axon, bt.axon) else target_axon

        # Build request endpoint from the synapse class
        request_name = synapse.__class__.__name__
        url = self._get_endpoint_url(target_axon, request_name)

        # Preprocess synapse for making a request
        synapse = await self.preprocess_synapse_for_request(target_axon, synapse, response_timeout)

        timeout_settings = aiohttp.ClientTimeout(sock_connect=connect_timeout, sock_read=response_timeout)

        try:
            # Log outgoing request
            if log_requests_and_responses:
                self._log_outgoing_request(synapse)

            # Make the HTTP POST request
            async with (await self.session).post(
                url,
                headers=synapse.to_headers(),
                json=synapse.model_dump(),
                timeout=timeout_settings,
            ) as response:
                # Use synapse subclass' process_streaming_response method to yield the response chunks
                async for chunk in synapse.process_streaming_response(response):
                    yield chunk

                # OVERRIDE: DISABLE THIS AS I ALSO HAVE NO IDEA WHY WE EVEN NEED IT
                # json_response = synapse.extract_response_json(response)

                # OVERRIDE: DISABLE THIS AS WE DON'T NEED MOST OF IT
                # self.process_server_response(response, json_response, synapse)

                # Keep this as useful for logging ?
                synapse.dendrite.status_code = synapse.axon.status_code
                synapse.dendrite.status_message = synapse.axon.status_message

            # Set process time and log the response
            synapse.dendrite.process_time = str(time.time() - start_time)

        except Exception as e:
            self._handle_request_errors(synapse, request_name, e, connect_timeout, response_timeout)

        finally:
            if log_requests_and_responses:
                self._log_incoming_response(synapse)

            # OVERRIDE: DISABLE THIS AS IT SEEMS LIKE ITS NEVER USED
            # Log synapse event history
            # self.synapse_history.append(bt.Synapse.from_headers(synapse.to_headers()))

            # OVERRIDE: DISABLE THIS AS I DONT NEED IT
            # if deserialize:
            #     yield synapse.deserialize()
            # else:
            # yield synapse

    async def call(
        self,
        target_axon: Union[bt.AxonInfo, bt.axon],
        synapse: bt.Synapse = bt.Synapse(),
        connect_timeout: float = 2.0,
        response_timeout: float = 3.0,
        deserialize: bool = True,
        log_requests_and_responses: bool = True,
    ) -> bt.Synapse | Any:
        """
        Asynchronously sends a request to a specified Axon and processes the response.

        This function establishes a connection with a specified Axon, sends the encapsulated
        data through the Synapse object, waits for a response, processes it, and then
        returns the updated Synapse object.

        Args:
            target_axon (Union['bt.AxonInfo', 'bt.axon']): The target Axon to send the request to.
            synapse (bt.Synapse, optional): The Synapse object encapsulating the data. Defaults to a new bt.Synapse instance.
            timeout (float, optional): Maximum duration to wait for a response from the Axon in seconds. Defaults to 12.0.
            deserialize (bool, optional): Determines if the received response should be deserialized. Defaults to True.

        Returns:
            bt.Synapse: The Synapse object, updated with the response data from the Axon.
        """

        # Record start time
        start_time = time.time()
        target_axon = target_axon.info() if isinstance(target_axon, bt.axon) else target_axon

        # Build request endpoint from the synapse class
        request_name = synapse.__class__.__name__
        url = self._get_endpoint_url(target_axon, request_name=request_name)

        # Preprocess synapse for making a request
        synapse = await self.preprocess_synapse_for_request(target_axon, synapse, response_timeout)

        timeout_settings = aiohttp.ClientTimeout(sock_connect=connect_timeout, sock_read=response_timeout)

        try:
            # Make the HTTP POST request
            async with (await self.session).post(
                url,
                headers=synapse.to_headers(),
                json=synapse.dict(),
                timeout=timeout_settings,
            ) as response:
                # Extract the JSON response from the server
                json_response = await response.json()
                # Process the server response and fill synapse
                self.process_server_response(response, json_response, synapse)

            # Set process time and log the response
            synapse.dendrite.process_time = str(time.time() - start_time)

        except Exception as e:
            self._handle_request_errors(synapse, request_name, e, connect_timeout, response_timeout)

        finally:
            # Log synapse event history
            # self.synapse_history.append(bt.Synapse.from_headers(synapse.to_headers()))

            # Return the updated synapse object after deserializing if requested
            if deserialize:
                return synapse.deserialize()  # noqa: B012
            else:
                return synapse

    async def preprocess_synapse_for_request(
        self,
        target_axon_info: bt.AxonInfo,
        synapse: bt.Synapse,
        response_timeout: float,
    ) -> bt.Synapse:
        """
        Preprocesses the synapse for making a request. This includes building
        headers for Dendrite and Axon and signing the request.


        Returns:
            bt.Synapse: The preprocessed synapse.
        """
        # Set the timeout for the synapse
        synapse.timeout = response_timeout

        # Build the Dendrite headers using the local system's details

        # TODO: review why I need to add my ip here, and TerminalInfo??

        # synapse.dendrite = bt.TerminalInfo(
        #     ip=bt.networking.get_external_ip(),
        #     version=bt.__version_as_int__,
        #     nonce=time.monotonic_ns(),
        #     uuid=self.uuid,
        #     hotkey="5Hddm3iBFD2GLT5ik7LZnT3XJUnRnN8PoeCFgGQgawUVKNm8",
        # )

        # # Build the Axon headers using the target axon's details
        # synapse.axon = bt.TerminalInfo(
        #     ip=target_axon_info.ip,
        #     port=target_axon_info.port,
        #     hotkey=target_axon_info.hotkey,
        # )

        # Sign the request using the dendrite, axon info, and the synapse body hash
        # check the below values for htkey, axon hotkey, and stuff
        message = f"{synapse.dendrite.nonce}.{synapse.dendrite.hotkey}.{synapse.axon.hotkey}.{synapse.dendrite.uuid}.{synapse.body_hash}"  # noqa

        signed_message = await self._sign_mesage(message)

        synapse.dendrite.signature = signed_message

        return synapse

    def process_server_response(
        self,
        server_response: aiohttp.ClientResponse,
        json_response: dict,
        local_synapse: bt.Synapse,
    ):
        """
        Processes the server response, updates the local synapse state with the
        server's state and merges headers set by the server.

        Args:
            server_response (object): The `aiohttp <https://github.com/aio-libs/aiohttp>`_ response object from the server.
            json_response (dict): The parsed JSON response from the server.
            local_synapse (bt.Synapse): The local synapse object to be updated.

        Raises:
            None: But errors in attribute setting are silently ignored.
        """
        # Check if the server responded with a successful status code
        if server_response.status == 200:
            # If the response is successful, overwrite local synapse state with
            # server's state only if the protocol allows mutation. To prevent overwrites,
            # the protocol must set allow_mutation = False
            server_synapse = local_synapse.__class__(**json_response)
            for key in local_synapse.dict():
                try:  # noqa
                    # Set the attribute in the local synapse from the corresponding
                    # attribute in the server synapse
                    setattr(local_synapse, key, getattr(server_synapse, key))
                except Exception:  # noqa
                    # Ignore errors during attribute setting
                    pass

        # Extract server headers and overwrite None values in local synapse headers
        server_headers = bt.Synapse.from_headers(server_response.headers)  # type: ignore

        # Merge dendrite headers
        local_synapse.dendrite.__dict__.update(
            {
                **local_synapse.dendrite.dict(exclude_none=True),  # type: ignore
                **server_headers.dendrite.dict(exclude_none=True),  # type: ignore
            }
        )

        # Merge axon headers
        local_synapse.axon.__dict__.update(
            {
                **local_synapse.axon.dict(exclude_none=True),  # type: ignore
                **server_headers.axon.dict(exclude_none=True),  # type: ignore
            }
        )

        # Update the status code and status message of the dendrite to match the axon
        local_synapse.dendrite.status_code = local_synapse.axon.status_code  # type: ignore
        local_synapse.dendrite.status_message = local_synapse.axon.status_message  # type: ignore

    async def forward(
        self,
        axons: Union[
            list[Union[bt.AxonInfo, bt.axon]],
            Union[bt.AxonInfo, bt.axon],
        ],
        synapse: bt.Synapse = bt.Synapse(),
        deserialize: bool = True,
        run_async: bool = True,
        streaming: bool = False,
        # TODO: Add these back in
        connect_timeout: float = 1.5,
        response_timeout: float = 30,
        log_requests_and_responses: bool = True,
    ) -> list[Union[AsyncGenerator[Any, Any], bt.Synapse, bt.StreamingSynapse]]:
        is_list = True
        # If a single axon is provided, wrap it in a list for uniform processing
        if not isinstance(axons, list):
            is_list = False
            axons = [axons]

        # Check if synapse is an instance of the StreamingSynapse class or if streaming flag is set.
        is_streaming_subclass = issubclass(synapse.__class__, bt.StreamingSynapse)
        if streaming != is_streaming_subclass:
            logger.warning(
                f"Argument streaming is {streaming} while issubclass(synapse, StreamingSynapse) is {synapse.__class__.__name__}. This may cause unexpected behavior."
            )
        streaming = is_streaming_subclass or streaming

        async def query_all_axons(
            is_stream: bool,
        ) -> Union[AsyncGenerator[Any, Any], bt.Synapse, bt.StreamingSynapse]:
            async def single_axon_response(
                target_axon,
            ) -> Union[AsyncGenerator[Any, Any], bt.Synapse, bt.StreamingSynapse]:
                if is_stream:
                    # If in streaming mode, return the async_generator
                    return self.call_stream(
                        target_axon=target_axon,
                        synapse=synapse.model_copy(),  # type: ignore
                        response_timeout=response_timeout,
                        connect_timeout=connect_timeout,
                        log_requests_and_responses=log_requests_and_responses,
                        deserialize=deserialize,
                    )
                # If not in streaming mode, simply call the axon and get the response.
                return await self.call(
                    target_axon=target_axon,
                    synapse=synapse.copy(),  # type: ignore
                    response_timeout=response_timeout,
                    connect_timeout=connect_timeout,
                    deserialize=deserialize,
                )

            # If run_async flag is False, get responses one by one.
            if not run_async:
                return [await single_axon_response(target_axon) for target_axon in axons]  # type: ignore
            # If run_async flag is True, get responses concurrently using asyncio.gather().
            return await asyncio.gather(*(single_axon_response(target_axon) for target_axon in axons))  # type: ignore

        # Get responses for all axons.
        responses = await query_all_axons(streaming)
        # Return the single response if only one axon was targeted, else return all responses
        return responses[0] if len(responses) == 1 and not is_list else responses  # type: ignore

    def __repr__(self) -> str:
        """
        Returns a string representation of the Dendrite object, acting as a fallback for :func:`__str__()`.

        Returns:
            str: The string representation of the Dendrite object in the format :func:`dendrite(<user_wallet_address>)`.
        """
        return self.__str__()

    async def __aenter__(self):
        """
        Asynchronous context manager entry method.

        Enables the use of the ``async with`` statement with the Dendrite instance. When entering the context,
        the current instance of the class is returned, making it accessible within the asynchronous context.

        Returns:
            Dendrite: The current instance of the Dendrite class.

        Usage::

            async with Dendrite() as dendrite:
                await dendrite.some_async_method()
        """
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """
        Asynchronous context manager exit method.

        Ensures proper cleanup when exiting the ``async with`` context. This method will close the `aiohttp <https://github.com/aio-libs/aiohttp>`_ client session
        asynchronously, releasing any tied resources.

        Args:
            exc_type (Type[BaseException], optional): The type of exception that was raised.
            exc_value (BaseException, optional): The instance of exception that was raised.
            traceback (TracebackType, optional): A traceback object encapsulating the call stack at the point where the exception was raised.

        Usage::

            async with bt.dendrite( wallet ) as dendrite:
                await dendrite.some_async_method()

        Note:
            This automatically closes the session by calling :func:`__aexit__` after the context closes.
        """
        await self.aclose_session()
