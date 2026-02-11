"""Unit tests for store list command."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.store_models import StoreOperationResult, EntityListResponse
from cl_client_cli.main import cli

def test_store_list_success(mock_store_manager, sample_entity_list):
    """Test store list command."""
    # Configure mock to return success result
    mock_store_manager.list_entities.return_value = StoreOperationResult[EntityListResponse](
        success="Entities retrieved successfully",
        data=sample_entity_list,
    )

    # Run command
    runner = CliRunner()
    result = runner.invoke(cli, ["store", "list"])

    # Verify
    assert result.exit_code == 0
    assert "Entity 1" in result.output
    assert "Entity 2" in result.output
    mock_store_manager.list_entities.assert_called_once()

def test_store_list_with_pagination(mock_store_manager, sample_entity_list):
    """Test store list with pagination options."""
    mock_store_manager.list_entities.return_value = StoreOperationResult[EntityListResponse](
        success="Success",
        data=sample_entity_list,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["store", "list", "--page", "2", "--page-size", "10"])

    assert result.exit_code == 0
    # Verify pagination parameters were passed
    call_kwargs = mock_store_manager.list_entities.call_args[1]
    assert call_kwargs["page"] == 2
    assert call_kwargs["page_size"] == 10

def test_store_list_with_search(mock_store_manager, sample_entity_list):
    """Test store list with search query."""
    mock_store_manager.list_entities.return_value = StoreOperationResult[EntityListResponse](
        success="Success",
        data=sample_entity_list,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["store", "list", "--search", "test query"])

    assert result.exit_code == 0
    call_kwargs = mock_store_manager.list_entities.call_args[1]
    assert call_kwargs["search_query"] == "test query"

def test_store_list_error(mock_store_manager):
    """Test store list with error."""
    mock_store_manager.list_entities.return_value = StoreOperationResult[EntityListResponse](
        error="Unauthorized: Invalid token",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["store", "list"])

    assert result.exit_code != 0
    assert "Unauthorized" in result.output
