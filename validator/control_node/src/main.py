# TODO: rename core_node (they shoud all be nodes)

import asyncio
from validator.control_node.src.weights import calculate_and_schedule_weights as calculate_weights

# do the rest
from validator.control_node.src.score_results import score_results
from validator.control_node.src import refresh_participants, schedule_synthetic_queries
from validator.control_node.src.synthetic_data import refresh_synthetic_data


# TODO: better co-ordinate these
async def main() -> None:
    await asyncio.gather(
        calculate_weights.main(),
        score_results.main(),
        refresh_participants.main(),
        schedule_synthetic_queries.main(),
        refresh_synthetic_data.main(),
    )


if __name__ == "__main__":
    asyncio.run(main())
