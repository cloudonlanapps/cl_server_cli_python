"""Integration tests for store CLI commands.

Run with:
    pytest tests/test_integration/test_store_cli.py \
        --auth-url=http://localhost:8010 \
        --compute-url=http://localhost:8012 \
        --store-url=http://localhost:8011 \
        --username=admin \
        --password=admin
"""

import uuid
from pathlib import Path

import pytest
from click.testing import CliRunner

from cl_client_cli.main import cli
from cl_client.store_models import Entity, EntityListResponse, EntityVersion, StoreConfig
from .conftest import SyncTestHelper, parse_cli_json, parse_cli_json_list, assert_cli_success


@pytest.mark.integration
class TestStoreCLI:
    """Test store CLI commands against live services."""

    def test_store_create_and_get(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test store create and get commands with JSON output."""
        label = f"test_store_create_{uuid.uuid4().hex[:8]}"
        # Create entity
        create_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "--json",
                "store",
                "create",
                "--label",
                label,
                "--file",
                str(test_image),
            ],
        )

        # Parse and validate with SDK Entity model
        created_entity = parse_cli_json(create_result, Entity)
        # Handle MD5 duplication: server might return existing entity with different label
        assert created_entity.id is not None
        entity_id = created_entity.id

        # Get the created entity
        get_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "--json",
                "store",
                "get",
                str(entity_id),
            ],
        )

        # Parse and validate with SDK Entity model
        retrieved_entity = parse_cli_json(get_result, Entity)
        assert retrieved_entity.id == entity_id

    def test_store_list(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test store list command with JSON output."""
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "--json",
                "store",
                "list",
                "--page",
                "1",
                "--page-size",
                "10",
            ],
        )

        # Parse and validate with SDK EntityListResponse model
        data = parse_cli_json(result, EntityListResponse)
        assert data.pagination.page == 1
        assert data.pagination.page_size == 10
        assert isinstance(data.items, list)

    def test_store_update(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test store update command with JSON output."""
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
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "--json",
                "store",
                "update",
                str(entity_id),
                "--label",
                "test_store_update_after",
            ],
        )

        # Validate success response
        assert_cli_success(result, "Updated entity")

    def test_store_patch(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test store patch command with JSON output."""
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
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "--json",
                "store",
                "patch",
                str(entity_id),
                "--label",
                "test_store_patched",
            ],
        )

        # Validate success response
        assert_cli_success(result, "Updated entity")

    def test_store_delete(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test store delete command with JSON output."""
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
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "--json",
                "store",
                "delete",
                str(entity_id),
                "--yes",  # Auto-confirm
            ],
        )

        # Validate success response
        assert_cli_success(result, "Deleted entity")

    def test_store_versions(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test store versions command with JSON output."""
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
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "--json",
                "store",
                "versions",
                str(entity_id),
            ],
        )

        # Parse list of EntityVersion models
        versions = parse_cli_json_list(result, EntityVersion)
        assert len(versions) >= 1
        assert versions[0].version >= 1

    def test_store_admin_config(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test store admin config command with JSON output."""
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
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

        # Parse and validate with SDK StoreConfig model
        config = parse_cli_json(result, StoreConfig)
        assert hasattr(config, "guest_mode")
