"""Unit tests for store create command."""

import json
from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.store_models import StoreOperationResult, Entity
from cl_client_cli.main import cli

def test_store_create_collection(mock_store_manager, sample_collection, mandatory_args):
    """Test creating a collection."""
    mock_store_manager.create_entity.return_value = StoreOperationResult[Entity](
        success="Entity created successfully",
        data=sample_collection,
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        mandatory_args + ["store", "create", "--label", "Test Collection", "--collection"],
    )

    assert result.exit_code == 0
    # Parse JSON output and verify entity data
    output_data = json.loads(result.output)
    assert output_data["id"] == 2
    assert output_data["is_collection"] is True
    assert output_data["label"] == "Test Collection"
    call_kwargs = mock_store_manager.create_entity.call_args[1]
    assert call_kwargs["label"] == "Test Collection"
    assert call_kwargs["is_collection"] is True

def test_store_create_with_file(mock_store_manager, sample_entity, temp_image_file, mandatory_args):
    """Test creating entity with file upload."""
    mock_store_manager.create_entity.return_value = StoreOperationResult[Entity](
        success="Entity created successfully",
        data=sample_entity,
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        mandatory_args + [
            "store",
            "create",
            "--label",
            "Photo",
            "--description",
            "Test photo",
            "--file",
            str(temp_image_file),
        ],
    )

    assert result.exit_code == 0
    # Parse JSON output and verify entity data
    output_data = json.loads(result.output)
    assert output_data["id"] == 1
    assert output_data["label"] == "Test Entity"
    call_kwargs = mock_store_manager.create_entity.call_args[1]
    assert call_kwargs["label"] == "Photo"
    assert call_kwargs["description"] == "Test photo"
    assert call_kwargs["image_path"] is not None
