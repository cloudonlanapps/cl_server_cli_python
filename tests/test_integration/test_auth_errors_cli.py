"""Integration tests for authentication and authorization error handling.

Run with:
    pytest tests/test_integration/test_auth_errors_cli.py \
        --auth-url=http://localhost:8010 \
        --compute-url=http://localhost:8012 \
        --store-url=http://localhost:8011 \
        --username=admin \
        --password=admin
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from cl_client_cli.main import cli


@pytest.mark.integration
class TestAuthErrorsCLI:
    """Test authentication and authorization error handling in CLI."""

    def test_unauthenticated_store_read(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test store read operation without authentication."""
        # Execute CLI command without credentials
        result = cli_runner.invoke(
            cli,
            [
                "--store-url",
                cli_env["CL_STORE_URL"],
                "store",
                "list",
            ],
        )

        # Should fail with non-zero exit code
        assert result.exit_code != 0, "Command should fail without authentication"
        # Should show authentication error
        assert (
            "auth" in result.output.lower()
            or "unauthorized" in result.output.lower()
            or "401" in result.output
        )

    def test_unauthenticated_store_write(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test store write operation without authentication."""
        # Execute CLI command without credentials
        result = cli_runner.invoke(
            cli,
            [
                "--store-url",
                cli_env["CL_STORE_URL"],
                "store",
                "create",
                "--label",
                "test_unauth",
                "--file",
                str(test_image),
            ],
        )

        # Should fail with non-zero exit code
        assert result.exit_code != 0, "Command should fail without authentication"
        # Should show authentication error
        assert (
            "auth" in result.output.lower()
            or "unauthorized" in result.output.lower()
            or "401" in result.output
        )

    def test_unauthenticated_plugin(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test plugin operation without authentication."""
        # Execute CLI command without credentials
        result = cli_runner.invoke(
            cli,
            [
                "--compute-url",
                cli_env["CL_COMPUTE_URL"],
                "clip-embedding",
                "embed",
                str(test_image),
            ],
        )

        # Should fail with non-zero exit code
        assert result.exit_code != 0, "Command should fail without authentication"
        # Should show authentication error
        assert (
            "auth" in result.output.lower()
            or "unauthorized" in result.output.lower()
            or "401" in result.output
        )

    def test_insufficient_permissions_admin(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test admin operation without admin role."""
        # First create a non-admin user
        admin_create_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "users",
                "create",
                "--username",
                "test_nonadmin",
                "--password",
                "test_password",
                "--email",
                "nonadmin@example.com",
            ],
        )

        assert (
            admin_create_result.exit_code == 0
        ), f"Create failed: {admin_create_result.output}"

        # Try to use admin command as non-admin user
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                "test_nonadmin",
                "--password",
                "test_password",
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "store",
                "admin",
                "config",
            ],
        )

        # Should fail with non-zero exit code
        assert result.exit_code != 0, "Command should fail without admin permissions"
        # Should show permission error
        assert (
            "permission" in result.output.lower()
            or "forbidden" in result.output.lower()
            or "403" in result.output
            or "unauthorized" in result.output.lower()
        )

    def test_insufficient_permissions_write(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test write operation without write permission."""
        # First create a user with read-only permissions
        admin_create_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "users",
                "create",
                "--username",
                "test_readonly",
                "--password",
                "test_password",
                "--email",
                "readonly@example.com",
            ],
        )

        assert (
            admin_create_result.exit_code == 0
        ), f"Create failed: {admin_create_result.output}"

        # Try to create entity as read-only user
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                "test_readonly",
                "--password",
                "test_password",
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "store",
                "create",
                "--label",
                "test_write_fail",
                "--file",
                str(test_image),
            ],
        )

        # Should fail with non-zero exit code
        assert result.exit_code != 0, "Command should fail without write permissions"
        # Should show permission error
        assert (
            "permission" in result.output.lower()
            or "forbidden" in result.output.lower()
            or "403" in result.output
            or "unauthorized" in result.output.lower()
        )

    def test_guest_mode_read(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test read operation in guest mode (if enabled)."""
        # Execute CLI command without credentials
        result = cli_runner.invoke(
            cli,
            [
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "store",
                "admin",
                "config",
            ],
        )

        # In guest mode, should see config with guest mode enabled
        # If guest mode is disabled, should see authentication error
        # Either is acceptable behavior
        if result.exit_code == 0:
            # Guest mode is enabled - should show config
            assert "guest" in result.output.lower() or "config" in result.output.lower()
        else:
            # Guest mode is disabled - should show auth error
            assert (
                "auth" in result.output.lower()
                or "unauthorized" in result.output.lower()
                or "401" in result.output
            )
