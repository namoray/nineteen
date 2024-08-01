"""
This is a utility script for manually setting weights in the case of any issues
Use cases:
- Testing weight setting to see scores and help debug
- Emergencies if weight setting in the vali is facing issues - but the proxy is still working as expected [not recommended]

NOTE: this is not artificial weights / weight copying, it uses real values obtained by the validator proxy only.
It's just taking that part of the code, and making it independently runnable

Usage:
python manually_set_weights.py --env_file {youvr_vali_hotkey_env_file_here}
"""

from validator.control_center import control_center
from validator.weight_setting import calculations
import asyncio
from validator.db.db_management import db_manager


async def main():
    await control_center.resync_metagraph()
    await db_manager.initialize()
    total_scores = await calculations.calculate_scores_for_settings_weights(
        capacities_for_tasks=control_center.capacities_for_tasks,
        uid_to_uid_info=control_center.uid_to_uid_info,
        task_weights=control_center.task_weights,
    )
    weights, uids = control_center.weight_setter._get_processed_weights_and_uids(
        uid_to_uid_info=control_center.uid_to_uid_info,
        metagraph=control_center.metagraph,
        total_hotkey_scores=total_scores,
        netuid=19,
    )
    control_center.weight_setter._set_weights(
        wallet=control_center.wallet,
        netuid=19,
        processed_weight_uids=uids,
        processed_weights=weights,
    )


if __name__ == "__main__":
    result = asyncio.run(main())
