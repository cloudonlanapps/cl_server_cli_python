"""Unit tests for store intelligence commands."""

import json
from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.store_models import StoreOperationResult
from cl_client.intelligence_models import EntityIntelligenceData
from cl_client_cli.main import cli

def test_store_intelligence_success(mock_store_manager, sample_entity_intelligence: EntityIntelligenceData, mandatory_args):
    """Test store intelligence command."""
    mock_store_manager.get_entity_intelligence.return_value = StoreOperationResult(
        success="Intelligence data retrieved successfully",
        data=sample_entity_intelligence,
    )

    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["store", "intelligence", "1"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["overall_status"] == "completed"
    mock_store_manager.get_entity_intelligence.assert_called_once_with(entity_id=1)
