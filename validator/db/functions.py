import asyncio
from datetime import datetime, timedelta
import random
import json
from typing import List, Dict, Any, Optional, Union


from core import Task

import bittensor as bt

from validator.db.database import PSQLDB
from models import utility_models
from validator.db import sql
from asyncpg import Connection

from validator.models import PeriodScore, RewardData


MAX_TASKS_IN_DB_STORE = 1000
db_lock = asyncio.Lock()


async def insert_task_results(
    connection: Connection, task: str, result: utility_models.QueryResult, synapse: bt.Synapse, synthetic_query: bool
) -> None:
    row_count = await sql.select_count_of_rows_in_tasks(connection)

    if row_count >= MAX_TASKS_IN_DB_STORE + 10:
        await connection.execute(sql.delete_oldest_rows_from_tasks(connection, limit=10))

    data_to_store = {
        "result": result.model_dump(),
        "synapse": json.dumps(synapse.model_dump()),
        "synthetic_query": synthetic_query,
    }
    hotkey = result.miner_hotkey
    data = json.dumps(data_to_store)
    await sql.insert_task(connection, task, data, hotkey)


async def potentially_store_result_in_sql_lite_db(
    psql_db: PSQLDB, result: utility_models.QueryResult, task: Task, synapse: bt.Synapse, synthetic_query: bool
) -> None:
    # if task not in self.task_weights:
    #     bt.logging.error(f"{task} not in task weights in db_manager")
    #     return
    # TODO: Fix this
    target_percentage = 0.1  # self.task_weights[task]

    target_number_of_tasks_to_store = int(MAX_TASKS_IN_DB_STORE * target_percentage)
    async with psql_db.connection() as connection:
        number_of_these_tasks_already_stored = await sql.select_count_rows_of_task_stored_for_scoring(connection, task)
        if number_of_these_tasks_already_stored <= target_number_of_tasks_to_store:
            await insert_task_results(task.value, result, synapse, synthetic_query)
        else:
            actual_percentage = number_of_these_tasks_already_stored / MAX_TASKS_IN_DB_STORE
            probability_to_score_again = (target_percentage / actual_percentage - target_percentage) ** 4
            if random.random() < probability_to_score_again:
                await insert_task_results(task.value, result, synapse, synthetic_query)


async def select_and_delete_task_result(psql_db: PSQLDB, task: Task) -> Optional[Union[List[Dict[str, Any]], str]]:
    async with psql_db.connection() as connection:
        row = await sql.select_task_for_deletion(connection, task.value)

        checking_data, miner_hotkey = row
        checking_data_loaded = json.loads(checking_data)

        await sql.delete_specific_task(connection, task.value, checking_data)

    return checking_data_loaded, miner_hotkey


# TODO: refactor
async def insert_reward_data(
    connection: Connection,
    reward_data: RewardData,
) -> str:
    await sql.insert_reward_data(
        connection,
        (
            reward_data.id,
            reward_data.task,
            reward_data.axon_uid,
            reward_data.quality_score,
            reward_data.validator_hotkey,
            reward_data.miner_hotkey,
            reward_data.synthetic_query,
            reward_data.speed_scoring_factor,
            reward_data.response_time,
            reward_data.volume,
        ),
    )

    return reward_data.id


async def clean_tables_of_hotkeys(connection: Connection, miner_hotkeys: List[str]) -> None:
    async with db_lock:
        for hotkey in miner_hotkeys:
            await connection.execute(sql.delete_task_by_hotkey(), (hotkey,))
            await connection.execute(sql.delete_reward_data_by_hotkey(), (hotkey,))
            await connection.execute(sql.delete_uid_data_by_hotkey(), (hotkey,))
        await connection.commit()


async def delete_tasks_older_than_date(connection: Connection, minutes: int) -> None:
    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    cutoff_time_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")

    async with db_lock:
        await connection.execute(sql.delete_task_data_older_than(), (cutoff_time_str,))
        await connection.commit()


async def delete_data_older_than_date(connection: Connection, minutes: int) -> None:
    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    cutoff_time_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")

    await sql.delete_reward_data_older_than(connection, cutoff_time_str)
    await sql.delete_uid_data_older_than(connection, cutoff_time_str)
    await sql.delete_task_data_older_than(connection, cutoff_time_str)


async def fetch_recent_most_rewards_for_uid(
    connection: Connection, task: Task, miner_hotkey: str, quality_tasks_to_fetch: int = 50
) -> List[RewardData]:
    date = datetime.now().timestamp() - timedelta(hours=72).total_seconds()
    priority_results = await sql.select_recent_reward_data_for_a_task(connection, task.value, date, miner_hotkey)

    y = len(priority_results)
    fill_results = await sql.select_recent_reward_data(connection, date, miner_hotkey, quality_tasks_to_fetch - y)

    reward_data_list = [
        RewardData(
            id=row[0],
            task=row[1],
            axon_uid=row[2],
            quality_score=row[3],
            validator_hotkey=row[4],
            miner_hotkey=row[5],
            synthetic_query=row[6],
            speed_scoring_factor=row[7],
            response_time=row[8],
            volume=row[9],
            created_at=row[10],
        )
        for row in priority_results + fill_results
    ]

    return reward_data_list


async def fetch_hotkey_scores_for_task(
    connection: Connection,
    task: Task,
    miner_hotkey: str,
) -> List[PeriodScore]:
    rows = await sql.select_uid_period_scores_for_task(connection, task.value, miner_hotkey)

    period_scores = [
        PeriodScore(
            hotkey=miner_hotkey,
            period_score=row[0],
            consumed_volume=row[1],
            created_at=row[2],
        )
        for row in rows
    ]
    return sorted(period_scores, key=lambda x: x.created_at, reverse=True)
