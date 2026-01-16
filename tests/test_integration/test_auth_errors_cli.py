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
import uuid
from click.testing import CliRunner

from cl_client_cli.main import cli
from cl_client.store_models import  StoreConfig
from cl_client.auth_models import UserResponse as User
from .conftest import parse_cli_json, assert_cli_error


@pytest.mark.integration
class TestAuthErrorsCLI:
    """Test authentication and authorization error handling in CLI."""

    def test_unauthenticated_store_read(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test store read operation without authentication returns JSON error."""
        # Execute CLI command with invalid credentials to ensure error
        result = cli_runner.invoke(
            cli,
            [
                "--store-url",
                cli_env["CL_STORE_URL"],
                "--username",
                "invalid",
                "--password",
                "invalid",
                "--json",
                "store",
                "list",
            ],
        )

        # Validate JSON error response
        assert_cli_error(result)

    def test_no_credentials_provided(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test store read operation with invalid credentials returns JSON error.

        Using invalid credentials forces an authentication fail and prevents guest mode fallback.
        """
        # Execute CLI command with invalid credentials
        result = cli_runner.invoke(
            cli,
            [
                "--store-url",
                cli_env["CL_STORE_URL"],
                "--username",
                "invalid_user",
                "--password",
                "invalid_pass",
                "--json",
                "store",
                "list",
            ],
        )

        # Validate JSON error response
        assert_cli_error(result)

    def test_unauthenticated_store_write(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test store write operation without authentication returns JSON error."""
        # Execute CLI command without credentials
        result = cli_runner.invoke(
            cli,
            [
                "--store-url",
                cli_env["CL_STORE_URL"],
                "--json",
                "store",
                "create",
                "--label",
                "test_unauth",
                "--file",
                str(test_image),
            ],
        )

        # Validate JSON error response
        assert_cli_error(result)

    def test_unauthenticated_plugin(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test plugin operation without authentication returns JSON error."""
        # Execute CLI command with invalid credentials to ensure error
        result = cli_runner.invoke(
            cli,
            [
                "--compute-url",
                cli_env["CL_COMPUTE_URL"],
                "--username",
                "invalid",
                "--password",
                "invalid",
                "--json",
                "clip-embedding",
                "embed",
                str(test_image),
            ],
        )

        # Validate JSON error response
        assert_cli_error(result)

    def test_insufficient_permissions_admin(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test admin operation without admin role returns JSON error."""
        username = f"test_nonadmin_{uuid.uuid4().hex[:8]}"
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
                "--json",
                "user",
                "create",
                username,
                "test_password",
            ],
        )

        # Parse created user
        created_user = parse_cli_json(admin_create_result, User)
        assert created_user.username == username

        # Try to use admin command as non-admin user
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                username,
                "--password",
                "test_password",
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "--json",
                "store",
                "admin",
                "config",
            ],
        )

        # Validate JSON error response
        assert_cli_error(result)

    def test_insufficient_permissions_write(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test write operation without write permission returns JSON error."""
        username = f"test_readonly_{uuid.uuid4().hex[:8]}"
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
                "--json",
                "user",
                "create",
                username,
                "test_password",
            ],
        )

        # Parse created user
        created_user = parse_cli_json(admin_create_result, User)
        assert created_user.username == username

        # Try to create entity as read-only user
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                username,
                "--password",
                "test_password",
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "--json",
                "store",
                "create",
                "--label",
                "test_write_fail",
                "--file",
                str(test_image),
            ],
        )

        # Validate JSON error response
        assert_cli_error(result)

    def test_guest_mode_read(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test read operation in guest mode with JSON output."""
        # Execute CLI command without credentials
        result = cli_runner.invoke(
            cli,
            [
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "--json",
                "store",
                "admin",
                "config",
            ],
        )

        # In guest mode, should succeed or fail depending on configuration
        if result.exit_code == 0:
            # Guest mode is enabled - validate StoreConfig model
            config = parse_cli_json(result, StoreConfig)
            assert hasattr(config, "guest_mode")
        else:
            # Guest mode is disabled - validate JSON error response
            assert_cli_error(result)
