"""
Scores results for tasks by querying an external scoring server.
Selects tasks to score based on the number of results available.
Stores the scored results in the database and potentially posts stats to TauVision.
"""

import asyncio
import random
import json
import os
import binascii
from typing import Any, Dict
from dataclasses import dataclass

import httpx
from redis.asyncio import Redis

from core.logging import get_logger
from core.tasks import Task
from validator.db.src.database import PSQLDB
from validator.models import RewardData
from validator.utils import work_and_speed_functions, generic_utils as gutils
from validator.db.src import functions as db_functions, sql
from dotenv import load_dotenv

logger = get_logger(__name__)

load_dotenv()


@dataclass(frozen=True)
class Config:
    psql_db: PSQLDB
    redis_db: Redis
    validator_hotkey: str
    testnet: bool
    max_results_to_score_for_task: int = int(os.getenv("MAX_RESULTS_TO_SCORE_FOR_TASK", 100))
    minimum_tasks_to_start_scoring: int = int(os.getenv("MINIMUM_TASKS_TO_START_SCORING", 1))
    minimum_tasks_to_start_scoring_testnet: int = int(os.getenv("MINIMUM_TASKS_TO_START_SCORING_TESTNET", 1))
    external_server_url: str = os.getenv("EXTERNAL_SERVER_URL", "http://38.128.232.218:6920/")


async def load_config() -> Config:
    psql_db = PSQLDB()
    await psql_db.connect()
    redis_db = Redis(host=os.getenv("REDIS_HOST", "redis"))
    public_key_info = await gutils.get_public_keypair_info(redis_db)
    return Config(
        psql_db=psql_db,
        redis_db=redis_db,
        validator_hotkey=public_key_info.ss58_address,
        testnet=os.getenv("TESTNET", "false").lower() == "true",
    )


async def score_results(config: Config):
    consecutive_errors = 0

    while True:
        async with await config.psql_db.connection() as connection:
            tasks_and_results = await sql.select_tasks_and_number_of_results(connection)

        total_tasks_stored = sum(tasks_and_results.values())
        min_tasks_to_start_scoring = (
            config.minimum_tasks_to_start_scoring_testnet if config.testnet else config.minimum_tasks_to_start_scoring
        )

        if total_tasks_stored < min_tasks_to_start_scoring:
            await asyncio.sleep(5)
            continue

        task_to_score = Task(
            random.choices(list(tasks_and_results.keys()), weights=list(tasks_and_results.values()), k=1)[0]
        )

        data_and_hotkey = await db_functions.select_and_delete_task_result(config.psql_db, task_to_score)
        if data_and_hotkey is None:
            logger.warning(f"No data left to score for task {task_to_score}")
            continue

        checking_data, miner_hotkey = data_and_hotkey
        results, synthetic_query, synapse_dict_str = (
            checking_data["result"],
            checking_data["synthetic_query"],
            checking_data["synapse"],
        )
        synapse = json.loads(synapse_dict_str)

        data = {
            "synapse": synapse,
            "synthetic_query": synthetic_query,
            "result": results,
            "task": task_to_score.value,
        }

        task_result, consecutive_errors = await send_result_for_scoring(config, data, consecutive_errors)
        if task_result is None:
            sleep_time = min(60 * (2 ** (consecutive_errors - 1)), 300)  # Max sleep time of 5 minutes
            await asyncio.sleep(sleep_time)
            continue

        await process_and_store_score(
            config, task_to_score, results, synapse, miner_hotkey, task_result, synthetic_query
        )
        consecutive_errors = 0
        await asyncio.sleep(5)


async def send_result_for_scoring(
    config: Config, data: Dict[str, Any], consecutive_errors: int
) -> tuple[Dict[str, Any] | None, int]:
    async with httpx.AsyncClient(timeout=180) as client:
        try:
            response = await client.post(config.external_server_url + "check-result", json=data)
            response.raise_for_status()
            task_id = response.json().get("task_id")

            if task_id is None:
                if response.json().get("status") == "Busy":
                    logger.warning("There's already a task being checked, will sleep and try again...")
                    await asyncio.sleep(20)
                    return None, consecutive_errors
                else:
                    logger.error("Checking server seems broke, please check!")
                    return None, consecutive_errors + 1

            while True:
                await asyncio.sleep(3)
                task_response = await client.get(f"{config.external_server_url}check-task/{task_id}")
                task_response.raise_for_status()
                task_response_json = task_response.json()

                if task_response_json.get("status") != "Processing":
                    if task_response_json.get("status") == "Failed":
                        logger.error(f"Task {task_id} failed: {task_response_json.get('error')}")
                        return None, consecutive_errors + 1
                    break

            return task_response_json.get("result", {}), 0

        except httpx.HTTPError as http_err:
            logger.error(f"When scoring, HTTP error occurred: {http_err}")
            return None, consecutive_errors + 1


async def process_and_store_score(
    config: Config,
    task: Task,
    results: Dict[str, Any],
    synapse: Dict[str, Any],
    miner_hotkey: str,
    task_result: Dict[str, Any],
    synthetic_query: str,
) -> None:
    axon_scores = task_result.get("axon_scores", {})
    if axon_scores is None:
        logger.error(f"Axon scores is none; found in the response json: {task_result}")
        return

    volume = work_and_speed_functions.calculate_work(task=task, result=results, synapse=synapse)
    speed_scoring_factor = work_and_speed_functions.calculate_speed_modifier(task=task, result=results, synapse=synapse)

    for uid, quality_score in axon_scores.items():
        reward_data = RewardData(
            id=binascii.hexlify(os.urandom(16)).decode("utf-8"),
            task=task.value,
            axon_uid=int(uid),
            quality_score=quality_score,
            validator_hotkey=config.validator_hotkey,
            miner_hotkey=miner_hotkey,
            synthetic_query=synthetic_query,
            response_time=results["response_time"] if quality_score != 0 else None,
            volume=volume,
            speed_scoring_factor=speed_scoring_factor,
        )

        async with await config.psql_db.connection() as connection:
            await sql.insert_reward_data(connection, reward_data)

        logger.info(f"Successfully scored and stored data for task: {task}")


async def main():
    config = await load_config()
    try:
        await score_results(config)
    finally:
        await config.psql_db.close()
        await config.redis_db.aclose()


if __name__ == "__main__":
    asyncio.run(main())
