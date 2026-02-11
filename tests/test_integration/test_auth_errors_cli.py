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
from cl_client.store_models import StorePref
from cl_client.auth_models import UserResponse as User
from tests.conftest import parse_cli_json, assert_cli_error


@pytest.mark.integration
class TestAuthErrorsCLI:
    """Test authentication and authorization error handling in CLI."""

    def test_unauthenticated_store_read(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        mandatory_args: list[str],
    ):
        """Test store read operation without authentication returns JSON error."""
        # Execute CLI command with invalid credentials to ensure error
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--username",
                "invalid",
                "--password",
                "invalid",
                "--json",
                "store",
                "list",
            ],
            env=cli_env,
        )

        # Validate JSON error response
        assert_cli_error(result)

    def test_no_credentials_provided(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        mandatory_args: list[str],
    ):
        """Test store read operation with invalid credentials returns JSON error.

        Using invalid credentials forces an authentication fail and prevents guest mode fallback.
        """
        # Execute CLI command with invalid credentials
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--username",
                "invalid_user",
                "--password",
                "invalid_pass",
                "--json",
                "store",
                "list",
            ],
            env=cli_env,
        )

        # Validate JSON error response
        assert_cli_error(result)

    def test_unauthenticated_store_write(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
        mandatory_args: list[str],
    ):
        """Test store write operation without authentication returns JSON error."""
        # Execute CLI command without credentials
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--username",
                "invalid",
                "--password",
                "invalid",
                "--json",
                "store",
                "create",
                "--label",
                "test_unauth",
                "--file",
                str(test_image),
            ],
            env=cli_env,
        )

        # Validate JSON error response
        assert_cli_error(result)

    def test_unauthenticated_plugin(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
        mandatory_args: list[str],
    ):
        """Test plugin operation without authentication returns JSON error."""
        # Execute CLI command with invalid credentials to ensure error
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--username",
                "invalid",
                "--password",
                "invalid",
                "--json",
                "clip-embedding",
                "embed",
                str(test_image),
            ],
            env=cli_env,
        )

        # Validate JSON error response
        assert_cli_error(result)

    def test_insufficient_permissions_admin(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        mandatory_args: list[str],
    ):
        """Test admin operation without admin role returns JSON error."""
        username = f"test_nonadmin_{uuid.uuid4().hex[:8]}"
        # First create a non-admin user
        admin_create_result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--json",
                "admin", "user",
                "create",
                username,
                "test_password",
            ],
            env=cli_env,
        )

        # Parse created user
        created_user = parse_cli_json(admin_create_result, User)
        assert created_user.username == username

        # Try to use admin command as non-admin user
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--username",
                username,
                "--password",
                "test_password",
                "--json",
                "store",
                "admin",
                "config",
            ],
            env=cli_env,
        )

        # Validate JSON error response
        assert_cli_error(result)

    def test_insufficient_permissions_write(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
        mandatory_args: list[str],
    ):
        """Test write operation without write permission returns JSON error."""
        username = f"test_readonly_{uuid.uuid4().hex[:8]}"
        # First create a user with read-only permissions
        admin_create_result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--json",
                "admin", "user",
                "create",
                username,
                "test_password",
            ],
            env=cli_env,
        )

        # Parse created user
        created_user = parse_cli_json(admin_create_result, User)
        assert created_user.username == username

        # Try to create entity as read-only user
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--username",
                username,
                "--password",
                "test_password",
                "--json",
                "store",
                "create",
                "--label",
                "test_write_fail",
                "--file",
                str(test_image),
            ],
            env=cli_env,
        )

        # Validate JSON error response
        assert_cli_error(result)

    def test_guest_mode_read(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        mandatory_args: list[str],
    ):
        """Test read operation in guest mode with JSON output."""
        # Execute CLI command without credentials
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--json",
                "store",
                "admin",
                "config",
            ],
            env=cli_env,
        )

        # In guest mode, should succeed or fail depending on configuration
        if result.exit_code == 0:
            # Guest mode is enabled - validate StorePref model
            config = parse_cli_json(result, StorePref)
            assert hasattr(config, "guest_mode")
        else:
            # Guest mode is disabled - validate JSON error response
            assert_cli_error(result)
