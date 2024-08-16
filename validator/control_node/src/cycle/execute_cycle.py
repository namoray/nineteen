"""
A cycle consists of
- Refreshing metagraph to get nodes (if not refreshed for X time in the case of restarts)
- Handshaking with the nodes
- Gathering the contenders from the nodes by querying for capacities
- Deciding what % of each contender should be queried
- Scheduling synthetics according the the amount of volume I need to query
- Getting the contender_scores from the 429's, 500's and successful queries
- Calculating weights when the scoring period is expired
- Setting the weights on the nodes async while starting the next cycle
"""

from validator.control_node.src.main import Config
from validator.control_node.src.cycle import (
    refresh_nodes,
    refresh_contenders,
    # schedule_synthetic_queries,
    # calculate_and_schedule_weights,
)


async def single_cycle(config: Config) -> None:
    nodes = await refresh_nodes.get_and_store_nodes(config)
    nodes = await refresh_nodes.perform_handshakes(nodes, config)
    await refresh_contenders.get_contenders_from_nodes(config, nodes)
    # await schedule_synthetic_queries.schedule_synthetics_until_done(config)

    # Should be performed in parallel to the next cycle
    # await calculate_and_schedule_weights.get_and_set_weights(config)
