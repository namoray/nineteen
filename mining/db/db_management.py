import sqlite3
from typing import Dict
from core import Task, constants as core_cst, tasks_config as tcfg


from mining.db import sql
from threading import local

DEFUALT_CONCURRENCY_GROUPS = {
    Task.chat_mixtral: 1,
    Task.chat_llama_3: 2,
    Task.proteus_text_to_image: 3,
    Task.playground_text_to_image: 3,
    Task.dreamshaper_text_to_image: 3,
    Task.proteus_image_to_image: 3,
    Task.playground_image_to_image: 3,
    Task.dreamshaper_image_to_image: 3,
    Task.jugger_inpainting: 3,
    Task.avatar: 3,
    # Task.clip_image_embeddings: 3,  # disabled clip for now
}

DEFAULT_CONCURRENCY_GROUP_VALUES = {1: 7, 2: 7, 3: 1}


class DatabaseManager:
    def __init__(self):
        self.local_data = local()

    def get_connection(self):
        if not hasattr(self.local_data, "conn"):
            self.local_data.conn = sqlite3.connect(core_cst.VISION_DB)
        return self.local_data.conn

    def close(self):
        if hasattr(self.local_data, "conn"):
            self.local_data.conn.close()

    def read_miner_task_config(self, miner_hotkey: str) -> Dict[str, int]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(sql.select_tasks_and_number_of_results(), (miner_hotkey,))
        rows = cursor.fetchall()
        return rows

    def insert_default_task_configs(self, miner_hotkey: str) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()

        for task in Task:
            cursor.execute(
                sql.search_task_config(),
                (
                    task.value,
                    miner_hotkey,
                ),
            )
            if not cursor.fetchone():
                max_capacity = tcfg.TASK_TO_MAX_CAPACITY[task]
                default_capcity = max_capacity / 2
                concurrency_group_id = DEFUALT_CONCURRENCY_GROUPS[task]
                cursor.execute(
                    sql.insert_default_task_configs(),
                    (
                        task.value,
                        default_capcity,
                        concurrency_group_id,
                        miner_hotkey,
                    ),
                )
        for concurrency_group_id, concurrency_group_limit in DEFAULT_CONCURRENCY_GROUP_VALUES.items():
            cursor.execute(
                sql.search_concurrency_group_config(),
                (concurrency_group_id,),
            )
            if not cursor.fetchone():
                cursor.execute(
                    sql.insert_default_task_concurrency_group_configs(),
                    (concurrency_group_id, concurrency_group_limit),
                )
        conn.commit()

    def load_concurrency_groups(self) -> Dict[str, int]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(sql.load_concurrency_groups(), ())
        rows = cursor.fetchall()
        return {str(key): value for key, value in dict(rows).items()}

    def load_task_capacities(self, miner_hotkey: str) -> Dict[str, Dict[str, int]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(sql.load_task_capacities(), (miner_hotkey,))
        rows = cursor.fetchall()
        results = {}
        for row in rows:
            task, volume, concurrency_group_id = row
            results[task] = {"volume": volume, "concurrency_group_id": concurrency_group_id}
        return results


miner_db_manager = DatabaseManager()
