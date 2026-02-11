"""Unit tests for store get command."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.store_models import StoreOperationResult, Entity
from cl_client_cli.main import cli

def test_store_get_success(mock_store_manager, sample_entity):
    """Test store get command."""
    mock_store_manager.read_entity.return_value = StoreOperationResult[Entity](
        success="Entity retrieved successfully",
        data=sample_entity,
    )

    # Run command
    runner = CliRunner()
    result = runner.invoke(cli, ["store", "get", "1"])

    assert result.exit_code == 0
    assert "Test Entity" in result.output
    assert "Test description" in result.output
    mock_store_manager.read_entity.assert_called_once_with(entity_id=1, version=None)

def test_store_get_with_version(mock_store_manager, sample_entity):
    """Test store get with specific version."""
    mock_store_manager.read_entity.return_value = StoreOperationResult[Entity](
        success="Success",
        data=sample_entity,
    )

    # Run command
    runner = CliRunner()
    result = runner.invoke(cli, ["store", "get", "1", "--version", "2"])

    assert result.exit_code == 0
    call_kwargs = mock_store_manager.read_entity.call_args[1]
    assert call_kwargs["version"] == 2
