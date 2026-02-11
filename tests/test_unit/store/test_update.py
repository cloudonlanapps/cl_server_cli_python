"""Unit tests for store update command."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.store_models import StoreOperationResult, Entity
from cl_client_cli.main import cli

def test_store_update_success(mock_store_manager, sample_entity):
    """Test store update command."""
    mock_store_manager.update_entity.return_value = StoreOperationResult[Entity](
        success="Entity updated successfully",
        data=sample_entity,
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["store", "update", "1", "--label", "Updated Label"],
    )

    assert result.exit_code == 0
    assert "Updated entity" in result.output
    call_kwargs = mock_store_manager.update_entity.call_args[1]
    assert call_kwargs["entity_id"] == 1
    assert call_kwargs["label"] == "Updated Label"
