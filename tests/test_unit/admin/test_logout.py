"""Unit tests for admin logout command."""

from unittest.mock import patch
from click.testing import CliRunner
from cl_client_cli.main import cli

def test_logout(mandatory_args):
    """Test admin logout command."""
    with patch("cl_client_cli.common.clear_password_cache") as mock_clear:
        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["admin", "logout"])

        assert result.exit_code == 0
        assert "Logged out" in result.output or "success" in result.output.lower()
        mock_clear.assert_called_once()

def test_logout_json_output(mandatory_args):
    """Test admin logout with JSON output."""
    with patch("cl_client_cli.common.clear_password_cache") as mock_clear:
        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["--json", "admin", "logout"])

        assert result.exit_code == 0
        assert '"message"' in result.output
        mock_clear.assert_called_once()
