"""Unit tests for hls-streaming commands."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.models import JobResponse
from cl_client_cli.main import cli

def test_generate_manifest_polling_mode(mock_compute_client, temp_video_file):
    """Test hls-streaming generate-manifest in polling mode."""
    # Configure mock
    job = JobResponse(
        job_id="test-job-jkl",
        task_type="hls_streaming",
        status="completed",
        progress=100,
        params={},
        task_output={
            "manifest_url": "/output/manifest.m3u8",
            "segments": 10,
        },
        error_message=None,
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
    )
    mock_compute_client.hls_streaming.generate_manifest = AsyncMock(return_value=job)

    # Run command
    runner = CliRunner()
    result = runner.invoke(cli, ["compute", "hls-streaming", "generate-manifest", str(temp_video_file)])

    # Verify
    assert result.exit_code == 0
    assert "manifest.m3u8" in result.output
    mock_compute_client.hls_streaming.generate_manifest.assert_called_once()
