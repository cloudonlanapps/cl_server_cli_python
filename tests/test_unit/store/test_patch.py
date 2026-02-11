"""Unit tests for store patch command."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.store_models import StoreOperationResult, Entity
from cl_client_cli.main import cli

def test_store_patch_label(mock_store_manager, sample_entity):
    """Test store patch command for label."""
    mock_store_manager.patch_entity.return_value = StoreOperationResult[Entity](
        success="Entity patched successfully",
        data=sample_entity,
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["store", "patch", "1", "--label", "Patched Label"],
    )

    assert result.exit_code == 0
    call_kwargs = mock_store_manager.patch_entity.call_args[1]
    assert call_kwargs["entity_id"] == 1
    assert call_kwargs["label"] == "Patched Label"

def test_store_patch_soft_delete(mock_store_manager, sample_entity):
    """Test store patch for soft delete."""
    deleted_entity = Entity(id=1, label="Test", is_deleted=True)
    mock_store_manager.patch_entity.return_value = StoreOperationResult[Entity](
        success="Entity patched successfully",
        data=deleted_entity,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["store", "patch", "1", "--delete"])

    assert result.exit_code == 0
    assert "Deleted entity" in result.output
    call_kwargs = mock_store_manager.patch_entity.call_args[1]
    assert call_kwargs["is_deleted"] is True

def test_store_patch_restore(mock_store_manager, sample_entity):
    """Test store patch for restore."""
    mock_store_manager.patch_entity.return_value = StoreOperationResult[Entity](
        success="Entity patched successfully",
        data=sample_entity,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["store", "patch", "1", "--restore"])

    assert result.exit_code == 0
    assert "Restored entity" in result.output
    call_kwargs = mock_store_manager.patch_entity.call_args[1]
    assert call_kwargs["is_deleted"] is False
