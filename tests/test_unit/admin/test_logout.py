"""Unit tests for logout command."""

from unittest.mock import patch
from click.testing import CliRunner
from cl_client_cli.main import cli

def test_logout():
    """Test logout command."""
    with patch("cl_client_cli.common.clear_config_cache") as mock_clear:
        runner = CliRunner()
        result = runner.invoke(cli, ["logout"])

        assert result.exit_code == 0
        assert "Logged out" in result.output or "success" in result.output.lower()
        mock_clear.assert_called_once()

def test_logout_json_output():
    """Test logout with JSON output."""
    with patch("cl_client_cli.common.clear_config_cache") as mock_clear:
        runner = CliRunner()
        result = runner.invoke(cli, ["logout", "--json"])

        assert result.exit_code == 0
        assert '"message"' in result.output or '"status"' in result.output
        mock_clear.assert_called_once()
