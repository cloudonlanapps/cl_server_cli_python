"""Integration tests for user management CLI commands.

Run with:
    pytest tests/test_integration/test_user_management_cli.py \
        --auth-url=http://localhost:8010 \
        --compute-url=http://localhost:8012 \
        --store-url=http://localhost:8011 \
        --username=admin \
        --password=admin
"""

import pytest
from click.testing import CliRunner

from cl_client_cli.main import cli
from cl_client.auth_models import UserResponse as User
from .conftest import parse_cli_json, parse_cli_json_list, assert_cli_success


@pytest.mark.integration
class TestUserManagementCLI:
    """Test user management CLI commands against live services."""

    def test_user_create(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user create command with JSON output."""
        # Execute CLI command to create a user
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--json",
                "users",
                "create",
                "--username",
                "test_user_create",
                "--password",
                "test_password",
                "--email",
                "test@example.com",
            ],
        )

        # Parse and validate with SDK User model
        user = parse_cli_json(result, User)
        assert user.username == "test_user_create"
        assert user.id is not None

    def test_user_list(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user list command with JSON output."""
        # Execute CLI command to list users
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--json",
                "users",
                "list",
            ],
        )

        # Parse list of User models
        users = parse_cli_json_list(result, User)
        assert isinstance(users, list)
        assert len(users) >= 0  # May be empty or have users

    def test_user_get(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user get command with JSON output."""
        # First create a user to get
        create_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--json",
                "users",
                "create",
                "--username",
                "test_user_get",
                "--password",
                "test_password",
                "--email",
                "test_get@example.com",
            ],
        )

        # Parse created user to get ID
        created_user = parse_cli_json(create_result, User)
        user_id = created_user.id

        # Test get command
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--json",
                "users",
                "get",
                str(user_id),
            ],
        )

        # Parse and validate with SDK User model
        user = parse_cli_json(result, User)
        assert user.id == user_id
        assert user.username == "test_user_get"

    def test_user_update(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user update command with JSON output."""
        # First create a user to update
        create_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--json",
                "users",
                "create",
                "--username",
                "test_user_update",
                "--password",
                "test_password",
                "--email",
                "test_update@example.com",
            ],
        )

        # Parse created user to get ID
        created_user = parse_cli_json(create_result, User)
        user_id = created_user.id

        # Test update command
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--json",
                "users",
                "update",
                str(user_id),
                "--email",
                "updated@example.com",
            ],
        )

        # Parse and validate updated user
        updated_user = parse_cli_json(result, User)
        assert updated_user.id == user_id

    def test_user_delete(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user delete command with JSON output."""
        # First create a user to delete
        create_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--json",
                "users",
                "create",
                "--username",
                "test_user_delete",
                "--password",
                "test_password",
                "--email",
                "test_delete@example.com",
            ],
        )

        # Parse created user to get ID
        created_user = parse_cli_json(create_result, User)
        user_id = created_user.id

        # Test delete command
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--json",
                "users",
                "delete",
                str(user_id),
                "--yes",  # Auto-confirm
            ],
        )

        # Validate success response
        assert_cli_success(result, "deleted")

    def test_user_permissions_list(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user permissions list command with JSON output."""
        # First create a user
        create_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--json",
                "users",
                "create",
                "--username",
                "test_user_perms",
                "--password",
                "test_password",
                "--email",
                "test_perms@example.com",
            ],
        )

        # Parse created user to get ID
        created_user = parse_cli_json(create_result, User)
        user_id = created_user.id

        # Test permissions list command
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--json",
                "users",
                "permissions",
                "list",
                str(user_id),
            ],
        )

        # Parse and validate user with permissions
        user = parse_cli_json(result, User)
        assert user.id == user_id
        assert hasattr(user, "permissions")

    def test_user_permissions_add(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user permissions add command with JSON output."""
        # First create a user
        create_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--json",
                "users",
                "create",
                "--username",
                "test_user_add_perm",
                "--password",
                "test_password",
                "--email",
                "test_add_perm@example.com",
            ],
        )

        # Parse created user to get ID
        created_user = parse_cli_json(create_result, User)
        user_id = created_user.id

        # Test add permission command
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--json",
                "users",
                "permissions",
                "add",
                str(user_id),
                "--permission",
                "read",
            ],
        )

        # Parse and validate user with added permission
        user = parse_cli_json(result, User)
        assert user.id == user_id
        assert "read" in user.permissions

    def test_user_permissions_remove(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user permissions remove command with JSON output."""
        # First create a user
        create_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--json",
                "users",
                "create",
                "--username",
                "test_user_remove_perm",
                "--password",
                "test_password",
                "--email",
                "test_remove_perm@example.com",
            ],
        )

        # Parse created user to get ID
        created_user = parse_cli_json(create_result, User)
        user_id = created_user.id

        # First add a permission
        add_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--json",
                "users",
                "permissions",
                "add",
                str(user_id),
                "--permission",
                "write",
            ],
        )

        assert add_result.exit_code == 0, f"Add permission failed: {add_result.output}"

        # Test remove permission command
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--json",
                "users",
                "permissions",
                "remove",
                str(user_id),
                "--permission",
                "write",
            ],
        )

        # Parse and validate user with permission removed
        user = parse_cli_json(result, User)
        assert user.id == user_id
        assert "write" not in user.permissions
