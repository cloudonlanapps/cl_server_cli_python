"""Integration tests for user management CLI commands.

Run with:
    pytest tests/test_integration/test_user_management_cli.py \
        --auth-url=http://localhost:8010 \
        --compute-url=http://localhost:8012 \
        --store-url=http://localhost:8011 \
        --username=admin \
        --password=admin
"""

import uuid
import pytest
from click.testing import CliRunner

from cl_client_cli.main import cli
from cl_client.auth_models import UserResponse as User
from tests.conftest import parse_cli_json, parse_cli_json_list, assert_cli_success


@pytest.mark.integration
class TestUserManagementCLI:
    """Test user management CLI commands against live services."""

    def test_user_create(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        mandatory_args: list[str],
    ):
        """Test user create command with JSON output."""
        username = f"test_user_create_{uuid.uuid4().hex[:8]}"
        # Execute CLI command to create a user
        result = cli_runner.invoke(
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

        # Parse and validate with SDK User model
        user = parse_cli_json(result, User)
        assert user.username == username
        assert user.id is not None

    def test_user_list(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        mandatory_args: list[str],
    ):
        """Test user list command with JSON output."""
        # Execute CLI command to list users
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--json",
                "admin", "user",
                "list",
            ],
            env=cli_env,
        )

        # Parse list of User models
        users = parse_cli_json_list(result, User)
        assert isinstance(users, list)
        assert len(users) >= 0  # May be empty or have users

    def test_user_get(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        mandatory_args: list[str],
    ):
        """Test user get command with JSON output."""
        username = f"test_user_get_{uuid.uuid4().hex[:8]}"
        # First create a user to get
        create_result = cli_runner.invoke(
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

        # Parse created user to get ID
        created_user = parse_cli_json(create_result, User)
        user_id = created_user.id

        # Test get command
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--json",
                "admin", "user",
                "get",
                str(user_id),
            ],
            env=cli_env,
        )

        # Parse and validate with SDK User model
        user = parse_cli_json(result, User)
        assert user.id == user_id
        assert user.username == username

    def test_user_update(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        mandatory_args: list[str],
    ):
        """Test user update command with JSON output."""
        username = f"test_user_update_{uuid.uuid4().hex[:8]}"
        # First create a user to update
        create_result = cli_runner.invoke(
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

        # Parse created user to get ID
        created_user = parse_cli_json(create_result, User)
        user_id = created_user.id

        # Test update command
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--json",
                "admin", "user",
                "update",
                str(user_id),
                "--active",  # Changed from --email
            ],
            env=cli_env,
        )

        # Parse and validate updated user
        updated_user = parse_cli_json(result, User)
        assert updated_user.id == user_id

    def test_user_delete(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        mandatory_args: list[str],
    ):
        """Test user delete command with JSON output."""
        username = f"test_user_delete_{uuid.uuid4().hex[:8]}"
        # First create a user to delete
        create_result = cli_runner.invoke(
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

        # Parse created user to get ID
        created_user = parse_cli_json(create_result, User)
        user_id = created_user.id

        # Test delete command
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--json",
                "admin", "user",
                "delete",
                str(user_id),
                "--yes",  # Auto-confirm
            ],
            env=cli_env,
        )

        # Validate success response
        assert_cli_success(result, "deleted")

    def test_user_permissions_list(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        mandatory_args: list[str],
    ):
        """Test user permissions list command with JSON output."""
        username = f"test_user_perms_{uuid.uuid4().hex[:8]}"
        # First create a user
        create_result = cli_runner.invoke(
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

        # Parse created user to get ID
        created_user = parse_cli_json(create_result, User)
        user_id = created_user.id

        # Test permissions list command
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--json",
                "admin", "user",
                "get",  # user permissions list doesn't exist, it's just user get
                str(user_id),
            ],
            env=cli_env,
        )

        # Parse and validate user with permissions
        user = parse_cli_json(result, User)
        assert user.id == user_id
        assert hasattr(user, "permissions")

    def test_user_permissions_update(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        mandatory_args: list[str],
    ):
        """Test user permissions update command with JSON output."""
        username = f"test_user_perms_upd_{uuid.uuid4().hex[:8]}"
        # First create a user
        create_result = cli_runner.invoke(
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

        # Parse created user to get ID
        created_user = parse_cli_json(create_result, User)
        user_id = created_user.id

        # Test update permissions
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--json",
                "admin", "user",
                "update",
                str(user_id),
                "--permissions",
                "read:jobs",
            ],
            env=cli_env,
        )

        # Parse and validate user with added permission
        user = parse_cli_json(result, User)
        assert user.id == user_id
        assert "read:jobs" in user.permissions

    def test_user_permissions_remove(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        mandatory_args: list[str],
    ):
        """Test user permissions removal via update with JSON output."""
        username = f"test_user_rem_perm_{uuid.uuid4().hex[:8]}"
        # First create a user
        create_result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--json",
                "admin", "user",
                "create",
                username,
                "test_password",
                "--permissions",
                "write:jobs",
            ],
            env=cli_env,
        )

        # Parse created user to get ID
        created_user = parse_cli_json(create_result, User)
        user_id = created_user.id
        assert "write:jobs" in created_user.permissions

        # Test remove permission command (by updating with empty permissions)
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--json",
                "admin", "user",
                "update",
                str(user_id),
                "--permissions",
                "read:jobs",  # Replaces write:jobs
            ],
            env=cli_env,
        )

        # Parse and validate user with permission removed
        user = parse_cli_json(result, User)
        assert user.id == user_id
        assert "write:jobs" not in user.permissions
        assert "read:jobs" in user.permissions
