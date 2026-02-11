"""Unit tests for store delete command."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.store_models import StoreOperationResult
from cl_client_cli.main import cli

def test_store_delete_success(mock_store_manager, mandatory_args):
    """Test store delete command."""
    mock_store_manager.delete_entity.return_value = StoreOperationResult[None](
        success="Entity deleted successfully",
        data=None,
    )

    runner = CliRunner()
    # Use --yes flag to bypass confirmation
    result = runner.invoke(cli, mandatory_args + ["store", "delete", "1", "--yes"])

    assert result.exit_code == 0
    assert "Deleted entity" in result.output
    mock_store_manager.delete_entity.assert_called_once_with(entity_id=1)
