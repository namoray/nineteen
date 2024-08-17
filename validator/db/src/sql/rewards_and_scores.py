from validator.models import RewardData
from validator.utils import database_constants as dcst
from typing import List
from asyncpg import Connection
##### Insert


async def insert_reward_data(connection: Connection, data: RewardData) -> str:
    return await connection.fetchval(
        f"""
        INSERT INTO {dcst.TABLE_REWARD_DATA} (
            {dcst.COLUMN_ID}, {dcst.COLUMN_TASK}, {dcst.COLUMN_AXON_UID}, 
            {dcst.COLUMN_QUALITY_SCORE}, {dcst.COLUMN_VALIDATOR_HOTKEY}, 
            {dcst.COLUMN_MINER_HOTKEY}, {dcst.COLUMN_SYNTHETIC_QUERY}, 
            {dcst.COLUMN_SPEED_SCORING_FACTOR}, {dcst.COLUMN_RESPONSE_TIME}, {dcst.COLUMN_VOLUME}
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING {dcst.COLUMN_ID}
        """,
        data.id,
        data.task,
        data.axon_uid,
        data.quality_score,
        data.validator_hotkey,
        data.node_hotkey,
        data.synthetic_query,
        data.speed_scoring_factor,
        data.response_time,
        data.volume,
    )


async def insert_uid_record(connection: Connection, data: List[tuple]) -> None:
    await connection.executemany(
        f"""
        INSERT INTO {dcst.TABLE_UID_RECORDS} (
            {dcst.COLUMN_AXON_UID}, {dcst.COLUMN_MINER_HOTKEY}, {dcst.COLUMN_VALIDATOR_HOTKEY}, {dcst.COLUMN_TASK}, 
            {dcst.COLUMN_DECLARED_VOLUME}, {dcst.COLUMN_CONSUMED_VOLUME}, {dcst.COLUMN_TOTAL_REQUESTS_MADE}, 
            {dcst.COLUMN_REQUESTS_429}, {dcst.COLUMN_REQUESTS_500}, {dcst.COLUMN_PERIOD_SCORE}
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
        data,
    )


async def insert_task(connection: Connection, task_name: str, checking_data: str, hotkey: str) -> None:
    await connection.executemany(
        f"""
        INSERT INTO {dcst.TABLE_TASKS} ({dcst.COLUMN_TASK_NAME}, {dcst.COLUMN_CHECKING_DATA}, {dcst.COLUMN_MINER_HOTKEY}) 
        VALUES ($1, $2, $3)
        """,
        ((task_name, checking_data, hotkey),),
    )


##### Delete stuff


async def delete_task_by_hotkey(connection: Connection, hotkey: str) -> None:
    await connection.execute(
        f"""
        DELETE FROM {dcst.TABLE_TASKS} WHERE {dcst.COLUMN_MINER_HOTKEY} = $1
        """,
        hotkey,
    )


async def delete_reward_data_by_hotkey(connection: Connection, hotkey: str) -> None:
    await connection.execute(
        f"""
        DELETE FROM {dcst.TABLE_REWARD_DATA} WHERE {dcst.COLUMN_MINER_HOTKEY} = $1
        """,
        hotkey,
    )


async def delete_uid_data_by_hotkey(connection: Connection, hotkey: str) -> None:
    await connection.execute(
        f"""
        DELETE FROM {dcst.TABLE_UID_RECORDS} WHERE {dcst.COLUMN_MINER_HOTKEY} = $1
        """,
        hotkey,
    )


async def delete_task_data_older_than(connection: Connection, date: str) -> None:
    await connection.execute(
        f"""
        DELETE FROM {dcst.TABLE_TASKS} WHERE {dcst.COLUMN_CREATED_AT} < $1
        """,
        date,
    )


async def delete_reward_data_older_than(connection: Connection, date: str) -> None:
    await connection.execute(
        f"""
        DELETE FROM {dcst.TABLE_REWARD_DATA} WHERE {dcst.COLUMN_CREATED_AT} < $1
        """,
        date,
    )


async def delete_uid_data_older_than(connection: Connection, date: str) -> None:
    await connection.execute(
        f"""
        DELETE FROM {dcst.TABLE_UID_RECORDS} WHERE {dcst.COLUMN_CREATED_AT} < $1
        """,
        date,
    )


async def delete_oldest_rows_from_tasks(connection: Connection, limit: int = 10) -> None:
    await connection.execute(
        f"""
        DELETE FROM {dcst.TABLE_TASKS} 
        WHERE {dcst.COLUMN_ID} IN (
            SELECT {dcst.COLUMN_ID} FROM {dcst.TABLE_TASKS} ORDER BY {dcst.COLUMN_CREATED_AT} ASC LIMIT $1
        )
        """,
        limit,
    )


async def delete_specific_task(connection: Connection, task_name: str, checking_data: str) -> None:
    await connection.execute(
        f"""
        DELETE FROM {dcst.TABLE_TASKS} WHERE {dcst.COLUMN_TASK_NAME} = $1 AND {dcst.COLUMN_CHECKING_DATA} = $2
        """,
        task_name,
        checking_data,
    )


#### Select


async def select_tasks_and_number_of_results(connection: Connection) -> dict:
    rows = await connection.fetch(
        f"""
        SELECT {dcst.COLUMN_TASK_NAME}, COUNT(*) as count FROM {dcst.TABLE_TASKS} GROUP BY {dcst.COLUMN_TASK_NAME}
        """
    )
    return {row[dcst.COLUMN_TASK_NAME]: row["count"] for row in rows}


async def select_count_of_rows_in_tasks(connection: Connection) -> int:
    result = await connection.fetchval(
        f"""
        SELECT COUNT(*) FROM {dcst.TABLE_TASKS}
        """
    )
    return result


async def select_count_rows_of_task_stored_for_scoring(connection: Connection, task_name: str) -> int:
    result = await connection.fetchval(
        f"""
        SELECT COUNT(*) FROM {dcst.TABLE_TASKS} WHERE {dcst.COLUMN_TASK_NAME} = $1
        """,
        task_name,
    )
    return result


async def select_task_for_deletion(connection: Connection, task_name: str) -> tuple:
    return await connection.fetchrow(
        f"""
        SELECT t.{dcst.COLUMN_CHECKING_DATA}, t.{dcst.COLUMN_MINER_HOTKEY}
        FROM {dcst.TABLE_TASKS} t
        LEFT JOIN (
            SELECT {dcst.COLUMN_MINER_HOTKEY}, COUNT(*) as reward_count
            FROM {dcst.TABLE_REWARD_DATA}
            WHERE {dcst.COLUMN_TASK} = $1
            GROUP BY {dcst.COLUMN_MINER_HOTKEY}
        ) r ON t.{dcst.COLUMN_MINER_HOTKEY} = r.{dcst.COLUMN_MINER_HOTKEY}
        WHERE t.{dcst.COLUMN_TASK_NAME} = $1
        ORDER BY COALESCE(r.reward_count, 0) ASC
        LIMIT 1
        """,
        task_name,
    )


async def select_recent_reward_data_for_a_task(
    connection: Connection, task: str, date: str, node_hotkey: str
) -> List[tuple]:
    return await connection.fetch(
        f"""
        SELECT
            {dcst.COLUMN_ID},
            {dcst.COLUMN_TASK},
            {dcst.COLUMN_AXON_UID},
            {dcst.COLUMN_QUALITY_SCORE},
            {dcst.COLUMN_VALIDATOR_HOTKEY},
            {dcst.COLUMN_MINER_HOTKEY},
            {dcst.COLUMN_SYNTHETIC_QUERY},
            {dcst.COLUMN_SPEED_SCORING_FACTOR},
            {dcst.COLUMN_RESPONSE_TIME},
            {dcst.COLUMN_VOLUME},
            {dcst.COLUMN_CREATED_AT}
        FROM {dcst.TABLE_REWARD_DATA}
        WHERE {dcst.COLUMN_TASK} = $1
        AND {dcst.COLUMN_CREATED_AT} > $2
        AND {dcst.COLUMN_MINER_HOTKEY} = $3
        ORDER BY {dcst.COLUMN_CREATED_AT} DESC
        """,
        task,
        date,
        node_hotkey,
    )


async def select_recent_reward_data(connection: Connection, date: str, node_hotkey: str, limit: int) -> list[tuple]:
    return await connection.fetch(
        f"""
        SELECT
            {dcst.COLUMN_ID},
            {dcst.COLUMN_TASK},
            {dcst.COLUMN_AXON_UID},
            {dcst.COLUMN_QUALITY_SCORE},
            {dcst.COLUMN_VALIDATOR_HOTKEY},
            {dcst.COLUMN_MINER_HOTKEY},
            {dcst.COLUMN_SYNTHETIC_QUERY},
            {dcst.COLUMN_SPEED_SCORING_FACTOR},
            {dcst.COLUMN_RESPONSE_TIME},
            {dcst.COLUMN_VOLUME},
            {dcst.COLUMN_CREATED_AT}
        FROM {dcst.TABLE_REWARD_DATA}
        WHERE {dcst.COLUMN_CREATED_AT} > $1
        AND {dcst.COLUMN_MINER_HOTKEY} = $2
        ORDER BY {dcst.COLUMN_CREATED_AT} DESC
        LIMIT $3
        """,
        date,
        node_hotkey,
        limit,
    )
