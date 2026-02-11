"""Unit tests for store admin guest-mode command."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.store_models import StoreOperationResult
from cl_client_cli.main import cli

def test_store_admin_set_guest_mode(mock_store_manager, sample_store_pref, mandatory_args):
    """Test store admin set-guest-mode command."""
    mock_store_manager.update_guest_mode.return_value = StoreOperationResult(
        success="Configuration updated successfully",
        data=sample_store_pref,
    )

    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["admin", "store", "set-guest-mode", "false"])

    # Verify config was updated
    assert result.exit_code == 0
    assert "disabled" in result.output
    mock_store_manager.update_guest_mode.assert_called_once_with(guest_mode=False)
