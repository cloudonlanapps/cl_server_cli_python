"""Unit tests for admin login command."""

from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cl_client_cli.main import cli

def test_login_with_credentials(mandatory_args):
    """Test admin login with username and password."""
    # Mock get_session_manager
    with patch("cl_client_cli.admin.login.common.get_session_manager") as mock_get_session:
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        mock_get_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            cli,
            mandatory_args + ["--username", "testuser", "--password", "testpass", "admin", "login"]
        )

        assert result.exit_code == 0
        assert "testuser" in result.output or "Logged in" in result.output

def test_login_json_output(mandatory_args):
    """Test admin login with JSON output."""
    with patch("cl_client_cli.admin.login.common.get_session_manager") as mock_get_session:
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        mock_get_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            cli,
            mandatory_args + ["--json", "--username", "admin", "--password", "admin", "admin", "login"]
        )

        assert result.exit_code == 0
        assert '"message"' in result.output or "Logged in" in result.output
