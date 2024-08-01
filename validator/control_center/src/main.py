# TODO: Fill in here to orchestrate the synthetic data / calculate weights / get_rewards and manage particpants
# Probably just need a thread for each and run them

# TODO: rename core_node (they shoud all be nodes)

import asyncio
from validator.core.calculate_weights import main as calculate_weights

# do the rest
from validator.core.get_rewards import main as get_rewards
from validator.core.manage_participants import refresh_participants, scheduling_participants
from validator.core.store_synthetic_data import generate_synthetic_data


# TODO: better co-ordinate these
async def main() -> None:
    await asyncio.gather(
        calculate_weights.main(),
        get_rewards.main(),
        refresh_participants.main(),
        scheduling_participants.main(),
        generate_synthetic_data.main(),
    )


if __name__ == "__main__":
    asyncio.run(main())