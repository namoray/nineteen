import asyncio
import os
import threading

import numpy as np
from core.bittensor_overrides.chain_data import AxonInfo
from dataclasses import asdict
from validator.db.database import PSQLDB
from validator.db import sql
from core.logging import get_logger
import bittensor as bt

logger = get_logger(__name__)

# Replace with some global threading lock?
threading_lock = threading.Lock()


async def _sync_metagraph(metagraph: bt.metagraph, subtensor: bt.subtensor) -> None:
    logger.info("Resyncing the metagraph!")
    await asyncio.to_thread(metagraph.sync, subtensor=subtensor, lite=True)
    new_axons = []
    incentives = metagraph.incentive.tolist()
    stakes = metagraph.S.tolist()
    logger.debug(f"Incentives: {incentives}")
    for axon, uid, incentive, stake in zip(metagraph.axons, metagraph.uids, incentives, stakes):
        new_axon_info = AxonInfo(
            **asdict(axon),
            axon_uid=uid,
            incentive=incentive,
            netuid=metagraph.netuid,
            network=metagraph.network,
            stake=stake,
        )
        logger.debug(f"New axon info: {new_axon_info}")
        new_axons.append(new_axon_info)

    logger.info(f"Synced {len(new_axons)} axons from the metagraph")
    metagraph.axons = new_axons


async def _store_metagraph_info(psql_db: PSQLDB, metagraph: bt.metagraph) -> list[str]:
    axons = metagraph.axons

    async with await psql_db.connection() as connection:
        await sql.migrate_axons_to_axon_history(connection)
        await sql.insert_axon_info(connection, axons)
        logger.info(f"Stored {len(axons)} axons from the metagraph")


async def get_and_store_metagraph_info(
    psql_db: PSQLDB,
    metagraph: bt.metagraph,
    subtensor: bt.subtensor,
    sync: bool = True,
    run_once: bool = False,
    seconds_between_syncs: int | None = None,
):
    if run_once:
        if sync:
            await _sync_metagraph(metagraph, subtensor)

        await _store_metagraph_info(psql_db, metagraph)
    else:
        if seconds_between_syncs is None:
            raise ValueError("seconds_between_syncs must be set if run_once is set to False")
        while True:
            if sync:
                await _sync_metagraph(metagraph, subtensor)

            await _store_metagraph_info(psql_db, metagraph)

            logger.info(
                f"Stored {len(metagraph.axons)} axons from the metagraph. Now sleeping for {seconds_between_syncs} seconds."
            )
            await asyncio.sleep(seconds_between_syncs)


def set_for_dummy_run(metagraph: bt.metagraph) -> bool:
    # Don't need to set this, as it's a property derived from the axons
    # metagraph.hotkeys = ["test-hotkey1", "test-hotkey2"]

    metagraph.axons = [
        # Vali
        AxonInfo(
            version=1,
            ip="127.0.0.1",
            port=1,
            ip_type=4,
            hotkey="test-vali",
            coldkey="test-vali-ck",
            axon_uid=0,
            incentive=0,
            netuid=metagraph.netuid,
            network=metagraph.network,
            stake=50.0,
        ),
        # Miners
        AxonInfo(
            version=1,
            ip="127.0.0.1",
            port=1,
            ip_type=4,
            hotkey="test-hotkey1",
            coldkey="test-coldkey1",
            axon_uid=1,
            incentive=0.004,
            netuid=metagraph.netuid,
            network=metagraph.network,
            stake=30.0,
        ),
        AxonInfo(
            version=2,
            ip="127.0.0.1",
            port=2,
            ip_type=4,
            hotkey="test-hotkey2",
            coldkey="test-coldkey2",
            axon_uid=2,
            incentive=0.005,
            netuid=metagraph.netuid,
            network=metagraph.network,
            stake=20,
        ),
    ]
    metagraph.total_stake = np.array([50, 30, 20])
    sync = False
    return sync


async def main():
    # Remember to export ENV=test
    psql_db = PSQLDB()
    await psql_db.connect()
    subtensor = None
    netuid = int(os.getenv("NETUID", 19))
    dummy = os.getenv("DUMMY", "true").lower() == "true"
    run_once = os.getenv("RUN_ONCE", "true").lower() == "true"
    metagraph = bt.metagraph(
        netuid=netuid, network=os.getenv("NETWORK", "finney"), lite=True, sync=False
    )
    sync = True

    seconds_between_syncs = int(os.getenv("SECONDS_BETWEEN_SYNCS", 60 * 20))

    logger.warning(
        f"run_once: {run_once}",
    )

    if dummy:
        sync = set_for_dummy_run(metagraph)

    await get_and_store_metagraph_info(
        psql_db,
        metagraph,
        subtensor,
        sync=sync,
        run_once=run_once,
        seconds_between_syncs=seconds_between_syncs,
    )


if __name__ == "__main__":
    asyncio.run(main())
