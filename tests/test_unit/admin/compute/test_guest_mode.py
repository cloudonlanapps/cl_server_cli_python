"""Unit tests for admin compute guest-mode commands."""

from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner
from cl_client_cli.main import cli


@patch("cl_client_cli.admin.compute.guest_mode.common.get_session_manager")
def test_guest_mode_get_enabled(mock_get_session):
    """Test getting guest mode when enabled."""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    mock_compute_client = MagicMock()
    mock_compute_client.get_guest_mode = AsyncMock(return_value=True)
    mock_session.create_compute_client = MagicMock(return_value=mock_compute_client)
    mock_get_session.return_value = mock_session

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["admin", "compute", "guest-mode", "get"]
    )

    assert result.exit_code == 0
    assert "true" in result.output.lower() or "guest_mode" in result.output.lower()
    mock_compute_client.get_guest_mode.assert_called_once()


@patch("cl_client_cli.admin.compute.guest_mode.common.get_session_manager")
def test_guest_mode_get_disabled(mock_get_session):
    """Test getting guest mode when disabled."""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    mock_compute_client = MagicMock()
    mock_compute_client.get_guest_mode = AsyncMock(return_value=False)
    mock_session.create_compute_client = MagicMock(return_value=mock_compute_client)
    mock_get_session.return_value = mock_session

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["admin", "compute", "guest-mode", "get"]
    )

    assert result.exit_code == 0
    assert "false" in result.output.lower() or "guest_mode" in result.output.lower()


@patch("cl_client_cli.admin.compute.guest_mode.common.get_session_manager")
def test_guest_mode_set_enable(mock_get_session):
    """Test enabling guest mode."""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    mock_compute_client = MagicMock()
    mock_compute_client.update_guest_mode = AsyncMock()
    mock_session.create_compute_client = MagicMock(return_value=mock_compute_client)
    mock_get_session.return_value = mock_session

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["admin", "compute", "guest-mode", "set", "true"]
    )

    assert result.exit_code == 0
    mock_compute_client.update_guest_mode.assert_called_once_with(True)


@patch("cl_client_cli.admin.compute.guest_mode.common.get_session_manager")
def test_guest_mode_set_disable(mock_get_session):
    """Test disabling guest mode."""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    mock_compute_client = MagicMock()
    mock_compute_client.update_guest_mode = AsyncMock()
    mock_session.create_compute_client = MagicMock(return_value=mock_compute_client)
    mock_get_session.return_value = mock_session

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["admin", "compute", "guest-mode", "set", "false"]
    )

    assert result.exit_code == 0
    mock_compute_client.update_guest_mode.assert_called_once_with(False)


@patch("cl_client_cli.admin.compute.guest_mode.common.get_session_manager")
def test_guest_mode_get_error(mock_get_session):
    """Test guest mode get with error."""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    mock_compute_client = MagicMock()
    mock_compute_client.get_guest_mode = AsyncMock(side_effect=Exception("API error"))
    mock_session.create_compute_client = MagicMock(return_value=mock_compute_client)
    mock_get_session.return_value = mock_session

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["admin", "compute", "guest-mode", "get"]
    )

    assert result.exit_code != 0
    assert "error" in result.output.lower()


@patch("cl_client_cli.admin.compute.guest_mode.common.get_session_manager")
def test_guest_mode_set_error(mock_get_session):
    """Test guest mode set with error."""
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()
    mock_compute_client = MagicMock()
    mock_compute_client.update_guest_mode = AsyncMock(side_effect=Exception("Permission denied"))
    mock_session.create_compute_client = MagicMock(return_value=mock_compute_client)
    mock_get_session.return_value = mock_session

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["admin", "compute", "guest-mode", "set", "true"]
    )

    assert result.exit_code != 0
    assert "error" in result.output.lower() or "permission" in result.output.lower()
