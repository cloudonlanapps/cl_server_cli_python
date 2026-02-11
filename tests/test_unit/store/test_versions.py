"""Unit tests for store versions command."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.store_models import StoreOperationResult
from cl_client_cli.main import cli

def test_store_versions_success(mock_store_manager, sample_versions, mandatory_args):
    """Test store versions command."""
    mock_store_manager.get_versions.return_value = StoreOperationResult[list](
        success="Version history retrieved successfully",
        data=sample_versions,
    )

    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["store", "versions", "1"])

    assert result.exit_code == 0
    assert "Version 1" in result.output
    assert "Version 2" in result.output
    mock_store_manager.get_versions.assert_called_once_with(1)
