import asyncio
from datetime import datetime, timedelta
import random
import json
from typing import List, Dict, Any, Optional, Union

import aiosqlite
from core import Task, constants as ccst

import bittensor as bt

from models import utility_models
from validation.db import sql
from validation.models import PeriodScore, RewardData, HotkeyRecord

MAX_TASKS_IN_DB_STORE = 1000
db_lock = asyncio.Lock()


class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.task_weights: Dict[Task, float] = {}

    async def initialize(self):
        self.conn = await aiosqlite.connect(ccst.VISION_DB)

    async def get_tasks_and_number_of_results(self) -> Dict[str, int]:
        async with db_lock:
            async with self.conn.execute(sql.select_tasks_and_number_of_results()) as cursor:
                rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows}

    async def _get_number_of_these_tasks_already_stored(self, task: Task) -> int:
        async with db_lock:
            async with self.conn.execute(sql.select_count_rows_of_task_stored_for_scoring(), (task.value,)) as cursor:
                row = await cursor.fetchone()
        return row[0]

    async def potentially_store_result_in_sql_lite_db(
        self, result: utility_models.QueryResult, task: Task, synapse: bt.Synapse, synthetic_query: bool
    ) -> None:
        if task not in self.task_weights:
            bt.logging.error(f"{task} not in task weights in db_manager")
            return
        target_percentage = self.task_weights[task]
        target_number_of_tasks_to_store = int(MAX_TASKS_IN_DB_STORE * target_percentage)
        number_of_these_tasks_already_stored = await self._get_number_of_these_tasks_already_stored(task)
        if number_of_these_tasks_already_stored <= target_number_of_tasks_to_store:
            await self.insert_task_results(task.value, result, synapse, synthetic_query)
        else:
            actual_percentage = number_of_these_tasks_already_stored / MAX_TASKS_IN_DB_STORE
            probability_to_score_again = (target_percentage / actual_percentage - target_percentage) ** 4
            if random.random() < probability_to_score_again:
                await self.insert_task_results(task.value, result, synapse, synthetic_query)

    async def insert_task_results(
        self, task: str, result: utility_models.QueryResult, synapse: bt.Synapse, synthetic_query: bool
    ) -> None:
        async with db_lock:
            async with self.conn.execute(sql.select_count_of_rows_in_tasks()) as cursor:
                row_count = (await cursor.fetchone())[0]

            if row_count >= MAX_TASKS_IN_DB_STORE + 10:
                await self.conn.execute(sql.delete_oldest_rows_from_tasks(limit=10))

            data_to_store = {
                "result": result.json(),
                "synapse": json.dumps(synapse.dict()),
                "synthetic_query": synthetic_query,
            }
            hotkey = result.miner_hotkey
            data = json.dumps(data_to_store)
            await self.conn.execute(sql.insert_task(), (task, data, hotkey))
            await self.conn.commit()

    async def select_and_delete_task_result(self, task: Task) -> Optional[Union[List[Dict[str, Any]], str]]:
        async with db_lock:
            async with self.conn.execute(sql.select_task_for_deletion(), (task.value, task.value)) as cursor:
                row = await cursor.fetchone()
            if row is None:
                return None

            checking_data, miner_hotkey = row
            checking_data_loaded = json.loads(checking_data)

            await self.conn.execute(sql.delete_specific_task(), (task.value, checking_data))
            await self.conn.commit()

        return checking_data_loaded, miner_hotkey

    async def insert_reward_data(
        self,
        reward_data: RewardData,
    ) -> str:
        async with db_lock:
            await self.conn.execute(
                sql.insert_reward_data(),
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
            await self.conn.commit()
        return reward_data.id

    async def clean_tables_of_hotkeys(self, miner_hotkeys: List[str]) -> None:
        async with db_lock:
            for hotkey in miner_hotkeys:
                await self.conn.execute(sql.delete_task_by_hotkey(), (hotkey,))
                await self.conn.execute(sql.delete_reward_data_by_hotkey(), (hotkey,))
                await self.conn.execute(sql.delete_uid_data_by_hotkey(), (hotkey,))
            await self.conn.commit()

    async def delete_tasks_older_than_date(self, minutes: int) -> None:
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        cutoff_time_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")

        async with db_lock:
            await self.conn.execute(sql.delete_task_data_older_than(), (cutoff_time_str,))
            await self.conn.commit()

    async def delete_data_older_than_date(self, minutes: int) -> None:
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        cutoff_time_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")

        async with db_lock:
            await self.conn.execute(sql.delete_reward_data_older_than(), (cutoff_time_str,))
            await self.conn.execute(sql.delete_uid_data_older_than(), (cutoff_time_str,))
            await self.conn.execute(sql.delete_task_data_older_than(), (cutoff_time_str,))

            await self.conn.commit()

    async def fetch_recent_most_rewards_for_uid(
        self, task: Task, miner_hotkey: str, quality_tasks_to_fetch: int = 50
    ) -> List[RewardData]:
        async with db_lock:
            async with self.conn.execute(
                sql.select_recent_reward_data_for_a_task(),
                (task.value, datetime.now().timestamp() - timedelta(hours=72).total_seconds(), miner_hotkey),
            ) as cursor:
                priority_results = await cursor.fetchall()

            y = len(priority_results)
            async with self.conn.execute(
                sql.select_recent_reward_data(),
                (
                    datetime.now().timestamp() - timedelta(hours=72).total_seconds(),
                    miner_hotkey,
                    quality_tasks_to_fetch - y,
                ),
            ) as cursor:
                fill_results = await cursor.fetchall()

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

    async def insert_uid_record(
        self,
        uid_record: HotkeyRecord,
        validator_hotkey: str,
    ) -> None:
        async with db_lock:
            await self.conn.execute(
                sql.insert_uid_record(),
                (
                    uid_record.hotkey,
                    uid_record.hotkey,
                    validator_hotkey,
                    uid_record.task.value,
                    uid_record.declared_volume,
                    uid_record.consumed_volume,
                    uid_record.total_requests_made,
                    uid_record.requests_429,
                    uid_record.requests_500,
                    uid_record.period_score,
                ),
            )
            await self.conn.commit()

    async def fetch_hotkey_scores_for_task(
        self,
        task: Task,
        miner_hotkey: str,
    ) -> List[PeriodScore]:
        async with db_lock:
            async with self.conn.execute(sql.select_uid_period_scores_for_task(), (task.value, miner_hotkey)) as cursor:
                rows = await cursor.fetchall()

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

    async def close(self):
        async with db_lock:
            await self.conn.close()


db_manager = DatabaseManager()
