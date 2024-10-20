from copy import deepcopy
import random

import pytest
from unittest.mock import AsyncMock, patch

from numpy.random import choice

from validator.query_node.src.select_contenders import select_contenders
from validator.models import ContenderSelectionInfo


dummy_contender_data = {
    "node_hotkey": "default_hotkey",
    "node_id": 0,
    "netuid": 0,
    "task": "default_task",
    "raw_capacity": 0.0,
    "capacity": 0.0,
    "capacity_to_score": 0.0
}

@pytest.mark.asyncio
@patch('validator.query_node.src.select_contenders.WEIGHT_QUALITY_SCORE', 3.0)
@patch('validator.query_node.src.select_contenders.WEIGHT_PERIOD_SCORE', 2.0)
@patch('validator.query_node.src.select_contenders.SOFTMAX_TEMPERATURE', 2.0)
@patch('validator.query_node.src.select_contenders.get_contenders_for_selection', new_callable=AsyncMock)
async def test_select_contenders(mock_get_contenders_for_selection):
    # Mock data
    mock_connection = AsyncMock()
    mock_task = "test_task"
    mock_contenders = [
        ContenderSelectionInfo(**dummy_contender_data, last_combined_quality_score=2.0, period_score=1.0),
        ContenderSelectionInfo(**dummy_contender_data, last_combined_quality_score=1.0, period_score=2.0),
        ContenderSelectionInfo(**dummy_contender_data, last_combined_quality_score=3.0, period_score=3.0)
    ]

    mock_get_contenders_for_selection.return_value = deepcopy(mock_contenders)

    result = await select_contenders(mock_connection, mock_task, top_x=2)

    assert len(result) == 2
    # order is not guaranteed
    # sort before asserting equality
    assert sorted(result, key=lambda x: x.period_score) == [mock_contenders[0].to_contender_model(), mock_contenders[2].to_contender_model()]


@pytest.mark.asyncio
@patch('validator.query_node.src.select_contenders.WEIGHT_QUALITY_SCORE', 3.0)
@patch('validator.query_node.src.select_contenders.WEIGHT_PERIOD_SCORE', 2.0)
@patch('validator.query_node.src.select_contenders.SOFTMAX_TEMPERATURE', 2.0)
@patch('validator.query_node.src.select_contenders.get_contenders_for_selection', new_callable=AsyncMock)
async def test_select_contenders(mock_get_contenders_for_selection):
    # Mock data
    mock_connection = AsyncMock()
    mock_task = "test_task"
    mock_contenders = []

    mock_get_contenders_for_selection.return_value = deepcopy(mock_contenders)

    result = await select_contenders(mock_connection, mock_task, top_x=2)

    assert len(result) == 0


def test_random_choice():
    """ tests that random.choice returns non zero probabilities of bottom contenders"""
    probabilities = [0.1, 0.2, 0.3, 0.4]

    found = 0
    # 1000 samples
    for _ in range(1000):
        selected_index = random.choices(range(len(probabilities)), weights=probabilities, k=1)[0]
        if selected_index == 0:
            found += 1
    assert found > 0
    # assert it is less than 10% of the time + margin)
    assert found < 1000 * (0.1 + 0.05)