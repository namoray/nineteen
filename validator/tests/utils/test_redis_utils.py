import pytest
from unittest.mock import AsyncMock
from validator.utils.redis_utils import add_json_to_redis_list

@pytest.mark.asyncio
async def test_add_json_to_redis_list():
    # Mock Redis instance
    redis_db = AsyncMock()
    
    # Test adding a JSON object to a Redis list
    json_to_add = {'key': 'value'}
    expected_json_string = '{"key": "value"}'
    queue = "test_queue"
    
    await add_json_to_redis_list(redis_db, queue, json_to_add)
    
    redis_db.rpush.assert_awaited_once_with(queue, expected_json_string)

@pytest.mark.asyncio
async def test_add_empty_json_to_redis_list():
    # Mock Redis instance
    redis_db = AsyncMock()
    
    # Test adding an empty JSON object to a Redis list
    json_to_add = {}
    expected_json_string = "{}"
    queue = "empty_queue"
    
    await add_json_to_redis_list(redis_db, queue, json_to_add)
    
    redis_db.rpush.assert_awaited_once_with(queue, expected_json_string)