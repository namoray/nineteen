import base64
import binascii
import io
from typing import AsyncGenerator
from validator.utils import query_constants as qcst, query_utils as qutils
from core import tasks_config as tcfg
from models import base_models, synapses
from core.bittensor_overrides.chain_data import AxonInfo
from PIL import Image
import random
import numpy as np
import time
from typing import Tuple
from core import bittensor_overrides as bt
from core.logging import get_logger


logger = get_logger(__name__)


def pil_to_base64(image: Image, format: str = "JPEG") -> str:
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


def base64_to_pil(image_b64: str) -> Image.Image:
    try:
        image_data = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(image_data))
        return image
    except binascii.Error:
        return None


def alter_image(
    pil_image: Image.Image,
) -> str:
    numpy_image = np.array(pil_image)
    for _ in range(3):
        rand_x, rand_y = (
            random.randint(0, pil_image.width - 1),
            random.randint(0, pil_image.height - 1),
        )

        for i in range(3):
            change = random.choice([-1, 1])
            numpy_image[rand_y, rand_x, i] = np.clip(int(numpy_image[rand_y, rand_x, i]) + change, 0, 255)

    pil_image = Image.fromarray(numpy_image)

    if pil_image.mode == "RGBA":
        pil_image = pil_image.convert("RGB")

    new_image = qutils.pil_to_base64(pil_image)
    return new_image


def alter_clip_body(
    body: base_models.ClipEmbeddingsIncoming,
) -> base_models.ClipEmbeddingsIncoming:
    if body.image_b64s is None:
        return body

    new_images = []
    for image in body.image_b64s:
        pil_image = qutils.base64_to_pil(image)
        new_image = alter_image(pil_image)
        new_images.append(new_image)

    body.image_b64s = new_images
    return body


async def consume_generator(generator: AsyncGenerator) -> None:
    async for _ in generator:
        pass


async def query_individual_axon(
    dendrite: bt.dendrite,
    axon: AxonInfo,
    uid: int,
    synapse: bt.Synapse,
    deserialize: bool = False,
    log_requests_and_responses: bool = True,
) -> Tuple[base_models.BaseSynapse, float]:
    operation_name = synapse.__class__.__name__
    if operation_name not in qcst.OPERATION_TIMEOUTS:
        logger.warning(f"Operation {operation_name} not in operation_to_timeout, this is probably a mistake / bug 🐞")

    timeouts = qcst.OPERATION_TIMEOUTS.get(operation_name, qcst.Timeouts(connect_timeout=15, response_timeout=15))

    start_time = time.time()

    if log_requests_and_responses:
        logger.info(f"Querying axon {uid} for {operation_name}")

    ### HERE TO ASSIST TESTING / DEV
    if "test" in axon.hotkey:
        if isinstance(synapse, synapses.Capacity):
            capacities = {}
            for task, config in tcfg.TASK_TO_CONFIG.items():
                capacities[task] = base_models.CapacityForTask(volume=config.max_capacity.volume / 2)
            response = synapses.Capacity(capacities=capacities)
            if deserialize:
                response = response.capacities
            start_time = start_time - 1.5  # add a lil extra time on
    else:
        response = await dendrite.forward(
            axons=axon,
            synapse=synapse,
            connect_timeout=timeouts.connect_timeout,
            response_timeout=timeouts.response_timeout,
            deserialize=deserialize,
            log_requests_and_responses=log_requests_and_responses,
            streaming=False,
        )

    # logger.debug(response.dendrite.status_message)

    return response, time.time() - start_time


async def query_individual_axon_stream(
    dendrite: bt.dendrite,
    axon: AxonInfo,
    axon_uid: int,
    synapse: bt.Synapse,
    deserialize: bool = False,
    log_requests_and_responses: bool = True,
):
    synapse_name = synapse.__class__.__name__
    if synapse_name not in qcst.OPERATION_TIMEOUTS:
        logger.warning(f"Operation {synapse_name} not in operation_to_timeout, this is probably a mistake / bug 🐞")
    if log_requests_and_responses:
        logger.info(f"Querying axon {axon_uid} for {synapse_name}")

    logger.debug(f"Querying axon {axon} for {synapse_name}")
    response = await dendrite.forward(
        axons=axon,
        synapse=synapse,
        connect_timeout=0.3,
        response_timeout=qcst.OPERATION_TIMEOUTS.get(synapse_name, 5),  # if X seconds without any data, its boinked
        deserialize=deserialize,
        log_requests_and_responses=log_requests_and_responses,
        streaming=True,
    )
    return response
