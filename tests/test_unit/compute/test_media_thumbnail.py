"""Unit tests for media-thumbnail commands."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.models import JobResponse
from cl_client_cli.main import cli

def test_generate_polling_mode(mock_compute_client, temp_image_file):
    """Test media-thumbnail generate in polling mode."""
    # Configure mock
    job = JobResponse(
        job_id="test-job-stu",
        task_type="media_thumbnail",
        status="completed",
        progress=100,
        params={},
        task_output={"thumbnail_path": "/output/thumb.jpg"},
        error_message=None,
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
    )
    mock_compute_client.media_thumbnail.generate = AsyncMock(return_value=job)

    # Run command with required width and height options
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["compute", "media-thumbnail", "generate", str(temp_image_file), "--width", "256", "--height", "256"],
    )

    # Verify
    assert result.exit_code == 0
    assert "test-job-stu" in result.output
    mock_compute_client.media_thumbnail.generate.assert_called_once()

def test_generate_with_size(mock_compute_client, temp_image_file):
    """Test media-thumbnail generate with size parameters."""
    # Configure mock
    job = JobResponse(
        job_id="test-job-vwx",
        task_type="media_thumbnail",
        status="completed",
        progress=100,
        params={},
        task_output={"thumbnail_path": "/output/thumb.jpg"},
        error_message=None,
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
    )
    mock_compute_client.media_thumbnail.generate = AsyncMock(return_value=job)

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "compute",
            "media-thumbnail",
            "generate",
            str(temp_image_file),
            "--width",
            "256",
            "--height",
            "256",
        ],
    )

    # Verify
    assert result.exit_code == 0
    # Check that generate was called with width/height parameters
    call_kwargs = mock_compute_client.media_thumbnail.generate.call_args[1]
    assert call_kwargs["width"] == 256
    assert call_kwargs["height"] == 256

def test_media_thumbnail_watch_mode(mock_compute_client, temp_image_file):
    """Test media-thumbnail generate with watch mode."""
    job = JobResponse(
        job_id="test-job-thumb-watch",
        task_type="media_thumbnail",
        status="completed",
        progress=100,
        params={},
        task_output={"thumbnail_path": "/output/thumb.jpg"},
        error_message=None,
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
    )

    async def mock_generate(**kwargs):
        if "on_complete" in kwargs:
            kwargs["on_complete"](job)
        return job

    mock_compute_client.media_thumbnail.generate = AsyncMock(side_effect=mock_generate)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "compute",
            "media-thumbnail",
            "generate",
            "--watch",
            str(temp_image_file),
            "--width",
            "256",
            "--height",
            "256",
        ],
    )

    assert result.exit_code == 0
    mock_compute_client.media_thumbnail.generate.assert_called_once()
