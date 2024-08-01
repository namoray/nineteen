"""
Test utilities for metagraph synchronization.
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from core.bittensor_overrides.chain_data import AxonInfo
from src.refresh_axons import (
    Config,
    load_config,
    fetch_axon_infos_from_metagraph,
    store_and_migrate_old_axons,
    get_and_store_metagraph_info,
)


def set_axons_for_testing(config: Config) -> None:
    config.metagraph.axons = [
        AxonInfo(
            version=1,
            ip="127.0.0.1",
            port=1,
            ip_type=4,
            hotkey="test-vali",
            coldkey="test-vali-ck",
            axon_uid=0,
            incentive=0,
            netuid=config.metagraph.netuid,
            network=config.metagraph.network,
            stake=50.0,
        ),
        AxonInfo(
            version=1,
            ip="127.0.0.1",
            port=1,
            ip_type=4,
            hotkey="test-hotkey1",
            coldkey="test-coldkey1",
            axon_uid=1,
            incentive=0.004,
            netuid=config.metagraph.netuid,
            network=config.metagraph.network,
            stake=30.0,
        ),
        AxonInfo(
            version=2,
            ip="127.0.0.1",
            port=2,
            ip_type=4,
            hotkey="test-hotkey2",
            coldkey="test-coldkey2",
            axon_uid=2,
            incentive=0.005,
            netuid=config.metagraph.netuid,
            network=config.metagraph.network,
            stake=20.0,
        ),
    ]
    config.metagraph.total_stake = np.array([50, 30, 20])
    config.sync = False


@pytest.fixture
def mock_config():
    config = load_config()
    config.psql_db = AsyncMock()
    config.metagraph = MagicMock()
    config.subtensor = MagicMock()
    return config


@pytest.mark.asyncio
async def test_fetch_axon_infos_from_metagraph(mock_config):
    mock_config.sync = True
    mock_config.metagraph.sync = AsyncMock()
    mock_config.metagraph.axons = [MagicMock()]
    mock_config.metagraph.uids = [1]
    mock_config.metagraph.incentive = np.array([0.1])
    mock_config.metagraph.S = np.array([100.0])

    await fetch_axon_infos_from_metagraph(mock_config)

    mock_config.metagraph.sync.assert_called_once()
    assert len(mock_config.metagraph.axons) == 1
    assert isinstance(mock_config.metagraph.axons[0], AxonInfo)


@pytest.mark.asyncio
async def test_store_and_migrate_old_axons(mock_config):
    mock_connection = AsyncMock()
    mock_config.psql_db.connection.return_value.__aenter__.return_value = mock_connection
    mock_config.metagraph.axons = [MagicMock()]

    with patch("src.refresh_axons.sql.migrate_axons_to_axon_history") as mock_migrate, patch(
        "src.refresh_axons.sql.insert_axon_info"
    ) as mock_insert:
        await store_and_migrate_old_axons(mock_config)

    mock_migrate.assert_called_once_with(mock_connection)
    mock_insert.assert_called_once_with(mock_connection, mock_config.metagraph.axons)


@pytest.mark.asyncio
async def test_get_and_store_metagraph_info(mock_config):
    mock_config.sync = True

    with patch("src.refresh_axons.fetch_axon_infos_from_metagraph") as mock_fetch, patch(
        "src.refresh_axons.store_and_migrate_old_axons"
    ) as mock_store:
        await get_and_store_metagraph_info(mock_config)

    mock_fetch.assert_called_once_with(mock_config)
    mock_store.assert_called_once_with(mock_config)


@pytest.mark.asyncio
async def test_get_and_store_metagraph_info_no_sync(mock_config):
    mock_config.sync = False

    with patch("src.refresh_axons.fetch_axon_infos_from_metagraph") as mock_fetch, patch(
        "src.refresh_axons.store_and_migrate_old_axons"
    ) as mock_store:
        await get_and_store_metagraph_info(mock_config)

    mock_fetch.assert_not_called()
    mock_store.assert_called_once_with(mock_config)


def test_set_axons_for_testing():
    config = MagicMock()
    config.metagraph.netuid = 1
    config.metagraph.network = "test"

    set_axons_for_testing(config)

    assert len(config.metagraph.axons) == 3
    assert isinstance(config.metagraph.axons[0], AxonInfo)
    assert config.metagraph.axons[0].hotkey == "test-vali"
    assert config.metagraph.axons[1].hotkey == "test-hotkey1"
    assert config.metagraph.axons[2].hotkey == "test-hotkey2"
    assert np.array_equal(config.metagraph.total_stake, np.array([50, 30, 20]))
    assert not config.sync
