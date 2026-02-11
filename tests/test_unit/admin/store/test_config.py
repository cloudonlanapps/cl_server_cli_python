"""Unit tests for store admin config command."""

import json
from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.store_models import StoreOperationResult
from cl_client_cli.main import cli

def test_store_admin_config(mock_store_manager, sample_store_pref, mandatory_args):
    """Test store admin config command."""
    mock_store_manager.get_pref.return_value = StoreOperationResult(
        success="Configuration retrieved successfully",
        data=sample_store_pref,
    )

    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["admin", "store", "config"])

    assert result.exit_code == 0
    # Parse JSON output and verify config data
    output_data = json.loads(result.output)
    assert output_data["guest_mode"] is False
    assert "updated_at" in output_data
    mock_store_manager.get_pref.assert_called_once()
