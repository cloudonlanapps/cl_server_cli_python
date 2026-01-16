"""Integration tests for store CLI commands.

Run with:
    pytest tests/test_integration/test_store_cli.py \
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
class TestStoreCLI:
    """Test store CLI commands against live services."""

    def test_store_create_and_get(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_image: Path,
    ):
        """Test store create and get commands with real file."""
        # Create entity
        create_result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--auth-url", cli_env["CL_AUTH_URL"],
                "--store-url", cli_env["CL_STORE_URL"],
                "store", "create",
                "--label", "test_store_create",
                "--file", str(test_image),
            ],
        )

        assert create_result.exit_code == 0, f"Create failed: {create_result.output}"
        assert "created" in create_result.output.lower() or "✓" in create_result.output

        # Extract entity ID from output
        # Output should contain "Entity ID: <id>" or similar
        lines = create_result.output.split("\n")
        entity_id = None
        for line in lines:
            if "id" in line.lower() and any(char.isdigit() for char in line):
                # Extract number from line
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    entity_id = numbers[0]
                    break

        assert entity_id is not None, f"Could not extract entity ID from output: {create_result.output}"

        # Get the created entity
        get_result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--auth-url", cli_env["CL_AUTH_URL"],
                "--store-url", cli_env["CL_STORE_URL"],
                "store", "get", entity_id,
            ],
        )

        assert get_result.exit_code == 0, f"Get failed: {get_result.output}"
        assert "test_store_create" in get_result.output
        assert entity_id in get_result.output

    def test_store_list(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
    ):
        """Test store list command with real data."""
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--auth-url", cli_env["CL_AUTH_URL"],
                "--store-url", cli_env["CL_STORE_URL"],
                "store", "list",
                "--page", "1",
                "--page-size", "10",
            ],
        )

        assert result.exit_code == 0, f"List failed: {result.output}"
        assert "page" in result.output.lower() or "entities" in result.output.lower()

    def test_store_update(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_helper,
        test_image: Path,
    ):
        """Test store update command."""
        # Create entity first
        entity_id = test_helper.create_test_entity(
            label="test_store_update_before",
            image_path=test_image,
        )

        assert entity_id is not None

        # Update the entity
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--auth-url", cli_env["CL_AUTH_URL"],
                "--store-url", cli_env["CL_STORE_URL"],
                "store", "update", str(entity_id),
                "--label", "test_store_update_after",
            ],
        )

        assert result.exit_code == 0, f"Update failed: {result.output}"
        assert "updated" in result.output.lower() or "✓" in result.output
        assert "test_store_update_after" in result.output

    def test_store_patch(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_helper,
        test_image: Path,
    ):
        """Test store patch command."""
        # Create entity first
        entity_id = test_helper.create_test_entity(
            label="test_store_patch",
            image_path=test_image,
        )

        assert entity_id is not None

        # Patch the entity
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--auth-url", cli_env["CL_AUTH_URL"],
                "--store-url", cli_env["CL_STORE_URL"],
                "store", "patch", str(entity_id),
                "--label", "test_store_patched",
            ],
        )

        assert result.exit_code == 0, f"Patch failed: {result.output}"
        assert "patched" in result.output.lower() or "updated" in result.output.lower() or "✓" in result.output

    def test_store_delete(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_helper,
        test_image: Path,
    ):
        """Test store delete command."""
        # Create entity first
        entity_id = test_helper.create_test_entity(
            label="test_store_delete",
            image_path=test_image,
        )

        assert entity_id is not None

        # Delete the entity
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--auth-url", cli_env["CL_AUTH_URL"],
                "--store-url", cli_env["CL_STORE_URL"],
                "store", "delete", str(entity_id),
                "--yes",  # Auto-confirm
            ],
        )

        assert result.exit_code == 0, f"Delete failed: {result.output}"
        assert "deleted" in result.output.lower() or "✓" in result.output

    def test_store_versions(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_helper,
        test_image: Path,
    ):
        """Test store versions command."""
        # Create entity first
        entity_id = test_helper.create_test_entity(
            label="test_store_versions",
            image_path=test_image,
        )

        assert entity_id is not None

        # Get versions
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--auth-url", cli_env["CL_AUTH_URL"],
                "--store-url", cli_env["CL_STORE_URL"],
                "store", "versions", str(entity_id),
            ],
        )

        assert result.exit_code == 0, f"Versions failed: {result.output}"
        assert "version" in result.output.lower() or str(entity_id) in result.output

    def test_store_admin_config(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
    ):
        """Test store admin config command."""
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--auth-url", cli_env["CL_AUTH_URL"],
                "--store-url", cli_env["CL_STORE_URL"],
                "store", "admin", "config",
            ],
        )

        assert result.exit_code == 0, f"Config failed: {result.output}"
        assert "guest" in result.output.lower() or "config" in result.output.lower()
