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


@pytest.mark.integration
class TestUserManagementCLI:
    """Test user management CLI commands against live services."""

    def test_user_create(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user create command."""
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

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "created" in result.output.lower() or "✓" in result.output
        assert "test_user_create" in result.output

    def test_user_list(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user list command."""
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
                "users",
                "list",
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "users" in result.output.lower() or "user" in result.output.lower()

    def test_user_get(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user get command."""
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

        assert create_result.exit_code == 0, f"Create failed: {create_result.output}"

        # Extract user ID from output
        lines = create_result.output.split("\n")
        user_id = None
        for line in lines:
            if "id" in line.lower() and any(char.isdigit() for char in line):
                import re

                numbers = re.findall(r"\d+", line)
                if numbers:
                    user_id = numbers[0]
                    break

        assert (
            user_id is not None
        ), f"Could not extract user ID from output: {create_result.output}"

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
                "users",
                "get",
                user_id,
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "test_user_get" in result.output
        assert user_id in result.output

    def test_user_update(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user update command."""
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

        assert create_result.exit_code == 0, f"Create failed: {create_result.output}"

        # Extract user ID
        lines = create_result.output.split("\n")
        user_id = None
        for line in lines:
            if "id" in line.lower() and any(char.isdigit() for char in line):
                import re

                numbers = re.findall(r"\d+", line)
                if numbers:
                    user_id = numbers[0]
                    break

        assert (
            user_id is not None
        ), f"Could not extract user ID from output: {create_result.output}"

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
                "users",
                "update",
                user_id,
                "--email",
                "updated@example.com",
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "updated" in result.output.lower() or "✓" in result.output
        assert "updated@example.com" in result.output

    def test_user_delete(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user delete command."""
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

        assert create_result.exit_code == 0, f"Create failed: {create_result.output}"

        # Extract user ID
        lines = create_result.output.split("\n")
        user_id = None
        for line in lines:
            if "id" in line.lower() and any(char.isdigit() for char in line):
                import re

                numbers = re.findall(r"\d+", line)
                if numbers:
                    user_id = numbers[0]
                    break

        assert (
            user_id is not None
        ), f"Could not extract user ID from output: {create_result.output}"

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
                "users",
                "delete",
                user_id,
                "--yes",  # Auto-confirm
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "deleted" in result.output.lower() or "✓" in result.output

    def test_user_permissions_list(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user permissions list command."""
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

        assert create_result.exit_code == 0, f"Create failed: {create_result.output}"

        # Extract user ID
        lines = create_result.output.split("\n")
        user_id = None
        for line in lines:
            if "id" in line.lower() and any(char.isdigit() for char in line):
                import re

                numbers = re.findall(r"\d+", line)
                if numbers:
                    user_id = numbers[0]
                    break

        assert (
            user_id is not None
        ), f"Could not extract user ID from output: {create_result.output}"

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
                "users",
                "permissions",
                "list",
                user_id,
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "permissions" in result.output.lower()

    def test_user_permissions_add(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user permissions add command."""
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

        assert create_result.exit_code == 0, f"Create failed: {create_result.output}"

        # Extract user ID
        lines = create_result.output.split("\n")
        user_id = None
        for line in lines:
            if "id" in line.lower() and any(char.isdigit() for char in line):
                import re

                numbers = re.findall(r"\d+", line)
                if numbers:
                    user_id = numbers[0]
                    break

        assert (
            user_id is not None
        ), f"Could not extract user ID from output: {create_result.output}"

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
                "users",
                "permissions",
                "add",
                user_id,
                "--permission",
                "read",
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert (
            "added" in result.output.lower()
            or "granted" in result.output.lower()
            or "✓" in result.output
        )

    def test_user_permissions_remove(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test user permissions remove command."""
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

        assert create_result.exit_code == 0, f"Create failed: {create_result.output}"

        # Extract user ID
        lines = create_result.output.split("\n")
        user_id = None
        for line in lines:
            if "id" in line.lower() and any(char.isdigit() for char in line):
                import re

                numbers = re.findall(r"\d+", line)
                if numbers:
                    user_id = numbers[0]
                    break

        assert (
            user_id is not None
        ), f"Could not extract user ID from output: {create_result.output}"

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
                "users",
                "permissions",
                "add",
                user_id,
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
                "users",
                "permissions",
                "remove",
                user_id,
                "--permission",
                "write",
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert (
            "removed" in result.output.lower()
            or "revoked" in result.output.lower()
            or "✓" in result.output
        )
