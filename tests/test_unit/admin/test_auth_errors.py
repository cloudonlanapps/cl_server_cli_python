"""Unit tests for authentication error scenarios."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.store_models import StoreOperationResult
from cl_client_cli.main import cli

def test_unauthorized_error(mock_store_manager, mandatory_args):
    """Test handling of 401 Unauthorized errors."""
    mock_store_manager.list_entities.return_value = StoreOperationResult(
        error="Unauthorized: Invalid token",
    )

    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["store", "list"])

    assert result.exit_code != 0
    assert "Unauthorized" in result.output

def test_forbidden_error(mock_store_manager, mandatory_args):
    """Test handling of 403 Forbidden errors."""
    mock_store_manager.get_pref.return_value = StoreOperationResult(
        error="Forbidden: Admin access required",
    )

    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["admin", "store", "config"])

    assert result.exit_code != 0
    assert "Forbidden" in result.output
