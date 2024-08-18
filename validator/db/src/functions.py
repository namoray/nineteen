import asyncio
from datetime import datetime, timedelta
import random
import json
from typing import List, Dict, Any, Optional, Union


from core.models import utility_models
from core.tasks import Task

from validator.db.src.database import PSQLDB
from validator.db.src.sql.rewards_and_scores import (
    select_count_of_rows_in_tasks,
    delete_oldest_rows_from_tasks,
    insert_task,
    select_count_rows_of_task_stored_for_scoring,
    select_task_for_deletion,
    sql_insert_reward_data,
    delete_reward_data_by_hotkey,
    delete_task_by_hotkey,
    delete_uid_data_by_hotkey,
    delete_task_data_older_than,
    delete_reward_data_older_than,
    delete_uid_data_older_than,
    select_recent_reward_data_for_a_task,
    select_recent_reward_data
)
from asyncpg import Connection

from validator.models import PeriodScore, RewardData


MAX_TASKS_IN_DB_STORE = 1000
db_lock = asyncio.Lock()


async def insert_task_results(
    connection: Connection, task: str, result: utility_models.QueryResult, synthetic_query: bool, payload: dict
) -> None:
    row_count = await select_count_of_rows_in_tasks(connection)

    if row_count >= MAX_TASKS_IN_DB_STORE + 10:
        await connection.execute(delete_oldest_rows_from_tasks(connection, limit=10))

    data_to_store = {
        "result": result.model_dump(mode="json"),
        "payload": json.dumps(payload),
        "synthetic_query": synthetic_query,
    }
    hotkey = result.node_hotkey
    data = json.dumps(data_to_store)
    await insert_task(connection, task, data, hotkey)


async def potentially_store_result_in_db(
    psql_db: PSQLDB, result: utility_models.QueryResult, task: Task, synthetic_query: bool, payload: dict
) -> None:
    # if task not in self.task_weights:
    #     bt.logging.error(f"{task} not in task weights in db_manager")
    #     return
    # TODO: Fix this
    target_percentage = 0.1  # self.task_weights[task]

    target_number_of_tasks_to_store = int(MAX_TASKS_IN_DB_STORE * target_percentage)
    async with await psql_db.connection() as connection:
        number_of_these_tasks_already_stored = await select_count_rows_of_task_stored_for_scoring(
            connection, task.value
        )
        if number_of_these_tasks_already_stored <= target_number_of_tasks_to_store:
            await insert_task_results(connection, task.value, result, payload, synthetic_query)
        else:
            actual_percentage = number_of_these_tasks_already_stored / MAX_TASKS_IN_DB_STORE
            probability_to_score_again = (target_percentage / actual_percentage - target_percentage) ** 4
            if random.random() < probability_to_score_again:
                await insert_task_results(connection, task.value, result, payload, synthetic_query)


async def select_and_delete_task_result(psql_db: PSQLDB, task: Task) -> Optional[Union[List[Dict[str, Any]], str]]:
    async with await psql_db.connection() as connection:
        row = await select_task_for_deletion(connection, task.value)

        checking_data, node_hotkey = row
        checking_data_loaded = json.loads(checking_data)

        # await sql.delete_specific_task(connection, task.value, checking_data)

    return checking_data_loaded, node_hotkey


# TODO: refactor
async def insert_reward_data(
    connection: Connection,
    reward_data: RewardData,
) -> str:
    await sql_insert_reward_data(
        connection,
        (
            reward_data.id,
            reward_data.task,
            reward_data.axon_uid,
            reward_data.quality_score,
            reward_data.validator_hotkey,
            reward_data.node_hotkey,
            reward_data.synthetic_query,
            reward_data.speed_scoring_factor,
            reward_data.response_time,
            reward_data.volume,
        ),
    )

    return reward_data.id


async def clean_tables_of_hotkeys(connection: Connection, node_hotkeys: List[str]) -> None:
    async with db_lock:
        for hotkey in node_hotkeys:
            await connection.execute(delete_task_by_hotkey(), (hotkey,))
            await connection.execute(delete_reward_data_by_hotkey(), (hotkey,))
            await connection.execute(delete_uid_data_by_hotkey(), (hotkey,))
        await connection.commit()


async def delete_tasks_older_than_date(connection: Connection, minutes: int) -> None:
    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    cutoff_time_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")

    async with db_lock:
        await connection.execute(delete_task_data_older_than(), (cutoff_time_str,))
        await connection.commit()


async def delete_data_older_than_date(connection: Connection, minutes: int) -> None:
    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    cutoff_time_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")

    await delete_reward_data_older_than(connection, cutoff_time_str)
    await delete_uid_data_older_than(connection, cutoff_time_str)
    await delete_task_data_older_than(connection, cutoff_time_str)


async def fetch_recent_most_rewards_for_uid(
    connection: Connection, task: Task, node_hotkey: str, quality_tasks_to_fetch: int = 50
) -> List[RewardData]:
    date = datetime.now() - timedelta(hours=72)
    priority_results = await select_recent_reward_data_for_a_task(connection, task.value, date, node_hotkey)

    y = len(priority_results)
    fill_results = await select_recent_reward_data(connection, date, node_hotkey, quality_tasks_to_fetch - y)

    reward_data_list = [
        RewardData(
            id=str(row[0]),
            task=row[1],
            axon_uid=row[2],
            quality_score=row[3],
            validator_hotkey=row[4],
            node_hotkey=row[5],
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
    node_hotkey: str,
) -> List[PeriodScore]:
    period_scores = await fetch_hotkey_scores_for_task(connection, task, node_hotkey)

    return sorted(period_scores, key=lambda x: x.created_at, reverse=True)
