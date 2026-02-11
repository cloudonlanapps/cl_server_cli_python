"""Unit tests for store admin audit-report command."""

import json
from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.store_models import StoreOperationResult
from cl_client_cli.main import cli

def test_store_admin_audit_report(mock_store_manager, sample_audit_report):
    """Test store admin audit-report command."""
    mock_store_manager.get_audit_report.return_value = StoreOperationResult(
        success="Audit report retrieved successfully",
        data=sample_audit_report,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["admin", "store", "audit-report"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "orphaned_files" in data
    mock_store_manager.get_audit_report.assert_called_once()
