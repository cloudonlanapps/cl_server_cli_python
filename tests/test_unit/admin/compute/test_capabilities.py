"""Unit tests for admin compute capabilities command."""

from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner
from cl_client_cli.main import cli


@patch("cl_client_cli.admin.compute.capabilities.common.get_session_manager")
def test_capabilities_success(mock_get_session):
    """Test admin compute capabilities command."""
    # Mock capabilities response as a Pydantic-like object
    mock_capabilities = MagicMock()
    mock_capabilities.model_dump_json = MagicMock(return_value='{"available_workers": 5, "tasks": ["face_detection"]}')

    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    mock_compute_client = MagicMock()
    mock_compute_client.get_capabilities = AsyncMock(return_value=mock_capabilities)
    mock_session.create_compute_client = MagicMock(return_value=mock_compute_client)
    mock_get_session.return_value = mock_session

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["admin", "compute", "capabilities"]
    )

    assert result.exit_code == 0
    mock_compute_client.get_capabilities.assert_called_once()


@patch("cl_client_cli.admin.compute.capabilities.common.get_session_manager")
def test_capabilities_error(mock_get_session):
    """Test admin compute capabilities command with error."""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    mock_compute_client = MagicMock()
    mock_compute_client.get_capabilities = AsyncMock(side_effect=Exception("Connection error"))
    mock_session.create_compute_client = MagicMock(return_value=mock_compute_client)
    mock_get_session.return_value = mock_session

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["admin", "compute", "capabilities"]
    )

    # Should handle error gracefully
    assert result.exit_code != 0
    assert "error" in result.output.lower() or "connection" in result.output.lower()
