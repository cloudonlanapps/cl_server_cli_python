"""Unit tests for compute error handling."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.models import JobResponse
from cl_client_cli.main import cli

def test_failed_job(mock_compute_client, temp_image_file):
    """Test handling of failed jobs."""
    # Configure mock to return failed job
    failed_job = JobResponse(
        job_id="test-job-fail",
        task_type="clip_embedding",
        status="failed",
        progress=50,
        params={},
        task_output=None,
        error_message="Processing error",
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
    )
    mock_compute_client.clip_embedding.embed_image = AsyncMock(return_value=failed_job)

    # Run command
    runner = CliRunner()
    result = runner.invoke(cli, ["compute", "clip-embedding", "embed", str(temp_image_file)])

    # Should show error but may exit 0 (depends on implementation)
    assert "failed" in result.output.lower() or "error" in result.output.lower()

def test_timeout_parameter(mock_compute_client, temp_image_file, completed_job):
    """Test timeout parameter is passed correctly."""
    mock_compute_client.clip_embedding.embed_image = AsyncMock(return_value=completed_job)

    # Run command with custom timeout
    runner = CliRunner()
    result = runner.invoke(
        cli, ["compute", "clip-embedding", "embed", "--timeout", "120", str(temp_image_file)]
    )

    # Verify timeout was passed
    assert result.exit_code == 0
    call_kwargs = mock_compute_client.clip_embedding.embed_image.call_args[1]
    assert call_kwargs["timeout"] == 120.0
