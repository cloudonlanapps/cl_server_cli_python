"""Unit tests for login command."""

from unittest.mock import AsyncMock, patch
from click.testing import CliRunner
from cl_client_cli.main import cli

def test_login_with_credentials():
    """Test login with username and password."""
    # Mock SessionManager
    with patch("cl_client.SessionManager") as mock_session_class:
        mock_session = AsyncMock()
        mock_session.login = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "login",
                "--username", "testuser",
                "--password", "testpass",
                "--auth-url", "http://localhost:8010",
                "--compute-url", "http://localhost:8012"
            ]
        )

        assert result.exit_code == 0
        assert "Logged in" in result.output or "testuser" in result.output

def test_login_json_output():
    """Test login with JSON output."""
    with patch("cl_client.SessionManager") as mock_session_class:
        mock_session = AsyncMock()
        mock_session.login = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "login",
                "--username", "testuser",
                "--password", "testpass",
                "--auth-url", "http://localhost:8010",
                "--json"
            ]
        )

        assert result.exit_code == 0
        assert '"status"' in result.output and '"success"' in result.output
