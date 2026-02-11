"""Unit tests for hash commands."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.models import JobResponse
from cl_client_cli.main import cli

def test_compute_polling_mode(mock_compute_client, temp_image_file):
    """Test hash compute in polling mode."""
    # Configure mock
    job = JobResponse(
        job_id="test-job-ghi",
        task_type="hash",
        status="completed",
        progress=100,
        params={},
        task_output={
            "phash": "abcdef1234567890",
            "dhash": "fedcba0987654321",
        },
        error_message=None,
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
    )
    mock_compute_client.hash.compute = AsyncMock(return_value=job)

    # Run command
    runner = CliRunner()
    result = runner.invoke(cli, ["compute", "hash", "compute", str(temp_image_file)])

    # Verify
    assert result.exit_code == 0
    assert "abcdef1234567890" in result.output
    assert "fedcba0987654321" in result.output
    mock_compute_client.hash.compute.assert_called_once()

def test_hash_watch_mode(mock_compute_client, temp_image_file):
    """Test hash compute with watch mode."""
    job = JobResponse(
        job_id="test-job-hash-watch",
        task_type="hash",
        status="completed",
        progress=100,
        params={},
        task_output={"phash": "abc123", "dhash": "def456"},
        error_message=None,
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
    )

    async def mock_compute(**kwargs):
        if "on_complete" in kwargs:
            kwargs["on_complete"](job)
        return job

    mock_compute_client.hash.compute = AsyncMock(side_effect=mock_compute)

    runner = CliRunner()
    result = runner.invoke(cli, ["compute", "hash", "compute", "--watch", str(temp_image_file)])

    assert result.exit_code == 0
    mock_compute_client.hash.compute.assert_called_once()
