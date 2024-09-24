from dotenv import load_dotenv
import os

from validator.control_node.src.set_weights import calculate_and_schedule_weights

load_dotenv(os.getenv("ENV_FILE", ".vali.env"))

import asyncio

from fiber.logging_utils import get_logger

from validator.control_node.src.score_results import score_results
from validator.control_node.src.control_config import load_config
from validator.control_node.src.synthetics import refresh_synthetic_data  # noqa
from validator.control_node.src.cycle import execute_cycle  # noqa


logger = get_logger(__name__)


async def main() -> None:
    config = load_config()
    await config.psql_db.connect()

    # NOTE: We could make separate threads if you wanted to be fancy
    await asyncio.gather(
        score_results.main(config),
        refresh_synthetic_data.main(config),
        execute_cycle.main(config),
        calculate_and_schedule_weights.set_weights_periodically(config),
    )


if __name__ == "__main__":
    asyncio.run(main())
