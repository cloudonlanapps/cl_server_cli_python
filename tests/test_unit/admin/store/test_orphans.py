"""Unit tests for store admin clear-orphans command."""

import json
from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.store_models import StoreOperationResult
from cl_client_cli.main import cli

def test_store_admin_clear_orphans(mock_store_manager, sample_cleanup_report, mandatory_args):
    """Test store admin clear-orphans command."""
    mock_store_manager.clear_orphans.return_value = StoreOperationResult(
        success="Orphans cleared successfully",
        data=sample_cleanup_report,
    )

    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["admin", "store", "clear-orphans", "--yes"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "files_deleted" in data
    mock_store_manager.clear_orphans.assert_called_once()
