import pytest
from unittest.mock import MagicMock, patch
from vali_new.core.uid_manager import UidManager, TASK_TO_VOLUME_TO_REQUESTS_CONVERSION
from vali_new.core.task import Task
from vali_new.validation.models import HotkeyRecord
from core import constants as ccst
@pytest.fixture
def uid_manager():
    return UidManager()

@pytest.mark.asyncio
async def test_task_not_in_conversion(uid_manager):
    task = Task.some_task_not_in_conversion
    hotkey = "test_hotkey"
    volume = 100.0

    with patch('vali_new.core.uid_manager.bt.logging.warning') as mock_warning:
        await uid_manager.handle_task_scoring_for_uid(task, hotkey, volume)
        mock_warning.assert_called_once()

@pytest.mark.asyncio
async def test_correct_number_of_requests(uid_manager):
    task = Task.playground_text_to_image
    hotkey = "test_hotkey"
    volume = 100.0

    await uid_manager.handle_task_scoring_for_uid(task, hotkey, volume)

    assert task in uid_manager.uid_records_for_tasks
    assert hotkey in uid_manager.uid_records_for_tasks[task]

    hotkey_record = uid_manager.uid_records_for_tasks[task][hotkey]
    expected_requests = max(int(volume / TASK_TO_VOLUME_TO_REQUESTS_CONVERSION[task]), 1)
    assert hotkey_record.synthetic_requests_still_to_make == expected_requests

@pytest.mark.asyncio
async def test_delay_between_requests_calculation(uid_manager):
    task = Task.playground_text_to_image
    hotkey = "test_hotkey"
    volume = 100.0

    await uid_manager.handle_task_scoring_for_uid(task, hotkey, volume)

    hotkey_record = uid_manager.uid_records_for_tasks[task][hotkey]
    expected_delay = (ccst.SCORING_PERIOD_TIME * 0.98) // (hotkey_record.synthetic_requests_still_to_make)
    expected_log = f"hotkey: {hotkey}, task: {task}, delay: {expected_delay}"

    with patch('vali_new.core.uid_manager.bt.logging.info') as mock_info:
        await uid_manager.handle_task_scoring_for_uid(task, hotkey, volume)
        mock_info.assert_called_with(expected_log)