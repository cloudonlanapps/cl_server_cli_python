"""Unit tests for store face commands."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.store_models import StoreOperationResult
from cl_client_cli.main import cli

def test_store_face_delete_success(mock_store_manager, mandatory_args):
    """Test store face delete command."""
    mock_store_manager.delete_face.return_value = StoreOperationResult(
        success="Face deleted successfully",
        data=None,
    )

    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["store", "face", "delete", "1", "--yes"])

    assert result.exit_code == 0
    assert "success" in result.output
    mock_store_manager.delete_face.assert_called_once_with(1)
