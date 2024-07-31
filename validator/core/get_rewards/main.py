# TODO: fill this in , a process to go to the GPU
# server and get all the rewards from the GPU
# then store into psql. P similar to what we already have

# Schema for the db
import asyncio
import random
from typing import Any, Dict

from core.logging import get_logger
from core.tasks import Task
from redis.asyncio import Redis

import httpx
from validator.db.database import PSQLDB
from validator.models import RewardData
from validator.utils import work_and_speed_functions, generic_utils as gutils
import json
from validator.db import functions as db_functions, sql
import os
import binascii

logger = get_logger(__name__)
# TODO: move these
MAX_RESULTS_TO_SCORE_FOR_TASK = 100
MINIMUM_TASKS_TO_START_SCORING = 1
MINIMUM_TASKS_TO_START_SCORING_TESTNET = 1

MIN_SECONDS_BETWEEN_SYNTHETICALLY_SCORING = 5
TESTNET = "testnet"

EXTERNAL_SERVER_URL = "http://38.128.232.218:6920/"


def _generate_uid() -> str:
    random_blob = os.urandom(16)
    uid = binascii.hexlify(random_blob).decode("utf-8")
    return uid


class Sleeper:
    def __init__(self) -> None:
        self.consecutive_errors = 0

    def _get_sleep_time(self) -> float:
        sleep_time = 0
        if self.consecutive_errors == 1:
            sleep_time = 60 * 1
        elif self.consecutive_errors == 2:
            sleep_time = 60 * 2
        elif self.consecutive_errors == 3:
            sleep_time = 60 * 4
        elif self.consecutive_errors >= 4:
            sleep_time = 60 * 5

        logger.error(f"Sleeping for {sleep_time} seconds after a http error with the orchestrator server")
        return sleep_time

    async def sleep(self) -> None:
        self.consecutive_errors += 1
        sleep_time = self._get_sleep_time()
        await asyncio.sleep(sleep_time)

    def reset_sleep_time(self) -> None:
        self.consecutive_errors = 0


class Scorer:
    def __init__(self, validator_hotkey: str, testnet: bool, psql_db: PSQLDB) -> None:
        self.am_scoring_results = False
        self.validator_hotkey = validator_hotkey
        self.testnet = testnet
        self.psql_db = psql_db
        self.sleeper = Sleeper()

    async def score_results(self):
        min_tasks_to_start_scoring = (
            MINIMUM_TASKS_TO_START_SCORING if self.testnet else MINIMUM_TASKS_TO_START_SCORING_TESTNET
        )
        logger.debug(f"Here! with {min_tasks_to_start_scoring}")
        while True:
            async with await self.psql_db.connection() as connection:
                tasks_and_number_of_results = await sql.select_tasks_and_number_of_results(connection)
                logger.debug(
                    f"Tasks and number of results: {tasks_and_number_of_results}",
                )
            total_tasks_stored = sum(tasks_and_number_of_results.values())

            if total_tasks_stored < min_tasks_to_start_scoring:
                await asyncio.sleep(5)
                continue

            else:
                task_to_score = random.choices(
                    list(tasks_and_number_of_results.keys()), weights=list(tasks_and_number_of_results.values()), k=1
                )[0]

                await self._check_scores_for_task(Task(task_to_score))
                await asyncio.sleep(5)

    async def _check_scores_for_task(self, task: Task) -> None:
        i = 0
        logger.info(f"Checking some results for task {task}")
        while i < MAX_RESULTS_TO_SCORE_FOR_TASK:
            data_and_hotkey = await db_functions.select_and_delete_task_result(self.psql_db, task)
            if data_and_hotkey is None:
                logger.warning(f"No data left to score for task {task}; iteration {i}")
                return
            checking_data, miner_hotkey = data_and_hotkey
            results, synthetic_query, synapse_dict_str = (
                checking_data["result"],
                checking_data["synthetic_query"],
                checking_data["synapse"],
            )
            results_json: Dict[str, Any] = results

            synapse = json.loads(synapse_dict_str)

            data = {
                "synapse": synapse,
                "synthetic_query": synthetic_query,
                "result": results_json,
                "task": task.value,
            }
            async with httpx.AsyncClient(timeout=180) as client:
                try:
                    j = 0
                    while True:
                        logger.info("Sending result to be scored...")
                        # TODO: REPLACE
                        response = await client.post(
                            EXTERNAL_SERVER_URL + "check-result",
                            json=data,
                        )
                        response.raise_for_status()
                        response_json = response.json()
                        task_id = response.json().get("task_id")
                        if task_id is None:
                            if response_json.get("status") == "Busy":
                                logger.warning(
                                    f"Attempt: {j}; There's already a task being checked, will sleep and try again..."
                                    f"\nresponse: {response.json()}"
                                )
                                await asyncio.sleep(20)
                                j += 1
                            else:
                                logger.error(
                                    "Checking server seems broke, please check!" f"response: {response.json()}"
                                )
                                await self.sleeper.sleep()
                                break

                        else:
                            break

                    # Ping the check-task endpoint until the task is complete
                    while True:
                        await asyncio.sleep(3)
                        task_response = await client.get(f"{EXTERNAL_SERVER_URL}check-task/{task_id}")
                        task_response.raise_for_status()
                        task_response_json = task_response.json()

                        if task_response_json.get("status") != "Processing":
                            task_status = task_response_json.get("status")
                            if task_status == "Failed":
                                logger.error(
                                    f"Task {task_id} failed: {task_response_json.get('error')}"
                                    f"\nTraceback: {task_response_json.get('traceback')}"
                                )
                                await self.sleeper.sleep()
                            break
                except httpx.HTTPStatusError as stat_err:
                    logger.error(f"When scoring, HTTP status error occurred: {stat_err}")
                    await self.sleeper.sleep()
                    continue

                except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ReadTimeout) as read_err:
                    logger.error(f"When scoring, Read timeout occurred: {read_err}")
                    await self.sleeper.sleep()
                    continue

                except httpx.HTTPError as http_err:
                    logger.error(f"When scoring, HTTP error occurred: {http_err}")
                    if isinstance(http_err, httpx.HTTPStatusError):
                        if http_err.response.status_code == 502:
                            logger.error("Is your orchestrator server running?")
                        else:
                            logger.error(f"Status code: {http_err.response.status_code}")
                    await self.sleeper.sleep()
                    continue

            self.sleeper.reset_sleep_time()
            try:
                task_result = task_response_json.get("result", {})
                axon_scores = task_result.get("axon_scores", {})
                if axon_scores is None:
                    logger.error(f"AXon scores is none; found in the response josn: {task_response_json}")
                    continue
            except (json.JSONDecodeError, KeyError) as parse_err:
                logger.error(f"Error occurred when parsing the response: {parse_err}")
                continue

            volume = work_and_speed_functions.calculate_work(task=task, result=results_json, synapse=synapse)
            speed_scoring_factor = work_and_speed_functions.calculate_speed_modifier(
                task=task, result=results_json, synapse=synapse
            )
            for uid, quality_score in axon_scores.items():
                # We divide max_expected_score whilst the orchestrator is still factoring this into the score
                # once it's removed from orchestrator, we'll remove it from here

                id = _generate_uid()

                reward_data = RewardData(
                    id=id,
                    task=task.value,
                    axon_uid=int(uid),
                    quality_score=quality_score,
                    validator_hotkey=self.validator_hotkey,  # fix
                    miner_hotkey=miner_hotkey,
                    synthetic_query=synthetic_query,
                    response_time=results_json["response_time"] if quality_score != 0 else None,
                    volume=volume,
                    speed_scoring_factor=speed_scoring_factor,
                )
                async with await self.psql_db.connection() as connection:
                    uid = await sql.insert_reward_data(connection, reward_data)

                data_to_post = reward_data.dict()
                data_to_post[TESTNET] = self.testnet

                # await post_stats.post_to_tauvision(
                #     data_to_post=data_to_post,
                #     keypair=self.keypair,
                #     data_type_to_post=post_stats.DataTypeToPost.REWARD_DATA,
                # )
                logger.info(f"Succesfully scored and stored data for task: {task}")

            i += 1


async def main():
    psql_db = PSQLDB()
    await psql_db.connect()

    redis_db = Redis(host="redis")

    public_key_info = await gutils.get_public_keypair_info(redis_db)

    scorer = Scorer(validator_hotkey=public_key_info.ss58_address, testnet=TESTNET, psql_db=psql_db)

    await scorer.score_results()


if __name__ == "__main__":
    asyncio.run(main())
