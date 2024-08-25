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

import httpx

from core import tasks_config as tcfg

from core.logging import get_logger
from core.tasks import Task
from validator.models import RewardData
from validator.utils import work_and_speed_functions
from validator.db.src import functions as db_functions
from validator.db.src.sql.rewards_and_scores import select_tasks_and_number_of_results, sql_insert_reward_data
from validator.control_node.src.control_config import Config
from core import constants as ccst

logger = get_logger(__name__)


async def test_external_server_connection(config: Config) -> bool:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(config.external_server_url)
            response.raise_for_status()
            logger.info("connected to the external scoring server.")
            return True
        except httpx.HTTPError as http_err:
            logger.error(f"Failed to connect to the external scoring server: {http_err}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error when connecting to the external scoring server: {e}")
            return False


async def wait_for_external_server(config: Config):
    max_sleep = 30
    sleep_duration = 5
    while True:
        if await test_external_server_connection(config):
            break
        logger.warning("Failed to connect to the external server. Retrying in 5 seconds...")

        await asyncio.sleep(min(sleep_duration, max_sleep))
        sleep_duration += 0.5


async def send_result_for_scoring(
    config: Config, checking_data: Dict[str, Any], node_hotkey: str, consecutive_errors: int
) -> tuple[Dict[str, Any] | None, int]:
    # TODO: Remove after debug
    rand_score = 1 if random.random() < 0.8 else 0 if random.random() < 0.9 else random.random()
    return {"node_scores": {checking_data["query_result"]["node_id"]: rand_score}}, 0
    async with httpx.AsyncClient(timeout=180) as client:
        try:
            response = await client.post(config.external_server_url + "check-result", json=checking_data)
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

            return task_response_json.get("query_result", {}), 0

        except httpx.HTTPError as http_err:
            logger.error(f"When scoring, HTTP error occurred: {http_err}")
            return None, consecutive_errors + 1


async def process_and_store_score(
    config: Config,
    task: Task,
    results: Dict[str, Any],
    payload: Dict[str, Any],
    node_hotkey: str,
    task_result: Dict[str, Any],
    synthetic_query: str,
) -> None:
    node_scores = task_result.get("node_scores", {})
    if node_scores is None:
        logger.error(f"Axon scores is none; found in the response json: {task_result}")
        return

    if task not in tcfg.TASK_TO_CONFIG:
        logger.error(f"Task {task} not found")
        return
    volume = work_and_speed_functions.calculate_work(task=task, result=results, steps=payload.get("steps"))
    speed_scoring_factor = work_and_speed_functions.calculate_speed_modifier(task=task, result=results, payload=payload)

    for node_id, quality_score in node_scores.items():
        reward_data = RewardData(
            id=binascii.hexlify(os.urandom(16)).decode("utf-8"),
            task=task.value,
            node_id=int(node_id),
            quality_score=quality_score,
            validator_hotkey=config.keypair.ss58_address,
            node_hotkey=node_hotkey,
            synthetic_query=synthetic_query,
            response_time=results["response_time"],
            volume=volume,
            speed_scoring_factor=speed_scoring_factor,
        )

        async with await config.psql_db.connection() as connection:
            await sql_insert_reward_data(connection, reward_data)

        logger.info(f"Successfully scored and stored data for task: {task}")


async def score_results(config: Config):
    while True:
        async with await config.psql_db.connection() as connection:
            tasks_and_results = await select_tasks_and_number_of_results(connection)

        total_tasks_stored = sum(tasks_and_results.values())
        min_tasks_to_start_scoring = 100 if config.netuid == ccst.PROD_NETUID else 1

        if total_tasks_stored < min_tasks_to_start_scoring:
            await asyncio.sleep(5)
            continue

        task_to_score = Task(
            random.choices(list(tasks_and_results.keys()), weights=list(tasks_and_results.values()), k=1)[0]
        )

        await score_task(config, task_to_score, max_tasks_to_score=200)


async def score_task(config: Config, task: Task, max_tasks_to_score: int):
    consecutive_errors = 0
    for _ in range(max_tasks_to_score):
        data_and_hotkey = await db_functions.select_and_delete_task_result(config.psql_db, task)
        if data_and_hotkey is None:
            logger.warning(f"No data left to score for task {task}")
            break

        raw_checking_data, node_hotkey = data_and_hotkey
        results, synthetic_query, payload_dict_str = (
            raw_checking_data["query_result"],
            raw_checking_data["synthetic_query"],
            raw_checking_data["payload"],
        )
        payload = json.loads(payload_dict_str)

        checking_data = {
            "payload": payload,
            "synthetic_query": synthetic_query,
            "query_result": results,
            "task": task.value,
        }

        task_result, consecutive_errors = await send_result_for_scoring(
            config, checking_data, node_hotkey, consecutive_errors
        )
        if task_result is None:
            sleep_time = min(60 * (2 ** (consecutive_errors - 1)), 300)  # Max sleep time of 5 minutes
            await asyncio.sleep(sleep_time)

        await process_and_store_score(
            config=config,
            task=task,
            results=results,
            payload=payload,
            node_hotkey=node_hotkey,
            task_result=task_result,
            synthetic_query=synthetic_query,
        )

        consecutive_errors = 0


async def main(config: Config):
    try:
        # await wait_for_external_server(config)
        await score_results(config)
    finally:
        await config.psql_db.close()


if __name__ == "__main__":
    asyncio.run(main())
