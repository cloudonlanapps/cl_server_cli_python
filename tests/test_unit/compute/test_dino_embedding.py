"""Unit tests for DINO embedding commands."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.models import JobResponse
from cl_client_cli.main import cli

def test_embed_polling_mode(mock_compute_client, temp_image_file, mandatory_args):
    """Test dino-embedding embed in polling mode."""
    # Configure mock
    job = JobResponse(
        job_id="test-job-456",
        task_type="dino_embedding",
        status="completed",
        progress=100,
        params={},
        task_output={"embedding": [0.1] * 384},
        error_message=None,
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
    )
    mock_compute_client.dino_embedding.embed_image = AsyncMock(return_value=job)

    # Run command
    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["compute", "dino-embedding", "embed", str(temp_image_file)])

    # Verify
    assert result.exit_code == 0
    assert "test-job-456" in result.output
    mock_compute_client.dino_embedding.embed_image.assert_called_once()

def test_dino_watch_mode(mock_compute_client, temp_image_file, mandatory_args):
    """Test dino-embedding with watch mode."""
    job = JobResponse(
        job_id="test-job-watch",
        task_type="dino_embedding",
        status="completed",
        progress=100,
        params={},
        task_output={"embedding": [0.1] * 384},
        error_message=None,
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
    )

    async def mock_embed(**kwargs):
        if "on_complete" in kwargs:
            kwargs["on_complete"](job)
        return job

    mock_compute_client.dino_embedding.embed_image = AsyncMock(side_effect=mock_embed)

    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["compute", "dino-embedding", "embed", "--watch", str(temp_image_file)])

    assert result.exit_code == 0
    mock_compute_client.dino_embedding.embed_image.assert_called_once()
