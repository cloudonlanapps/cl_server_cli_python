"""Unit tests for image-conversion commands."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.models import JobResponse
from cl_client_cli.main import cli

def test_convert_polling_mode(mock_compute_client, temp_image_file):
    """Test image-conversion convert in polling mode."""
    # Configure mock
    job = JobResponse(
        job_id="test-job-mno",
        task_type="image_conversion",
        status="completed",
        progress=100,
        params={},
        task_output={"output_path": "/output/image.png"},
        error_message=None,
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
    )
    mock_compute_client.image_conversion.convert = AsyncMock(return_value=job)

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        cli, ["compute", "image-conversion", "convert", str(temp_image_file), "--format", "png"]
    )

    # Verify
    assert result.exit_code == 0
    assert "test-job-mno" in result.output
    mock_compute_client.image_conversion.convert.assert_called_once()

def test_convert_with_quality(mock_compute_client, temp_image_file):
    """Test image-conversion convert with quality parameter."""
    # Configure mock
    job = JobResponse(
        job_id="test-job-pqr",
        task_type="image_conversion",
        status="completed",
        progress=100,
        params={},
        task_output={"output_path": "/output/image.jpg"},
        error_message=None,
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
    )
    mock_compute_client.image_conversion.convert = AsyncMock(return_value=job)

    # Run command
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "compute",
            "image-conversion",
            "convert",
            str(temp_image_file),
            "--format",
            "jpg",
            "--quality",
            "90",
        ],
    )

    # Verify
    assert result.exit_code == 0
    # Check that convert was called with quality parameter
    call_kwargs = mock_compute_client.image_conversion.convert.call_args[1]
    assert call_kwargs["quality"] == 90

def test_image_conversion_watch_mode(mock_compute_client, temp_image_file):
    """Test image-conversion convert with watch mode."""
    job = JobResponse(
        job_id="test-job-convert-watch",
        task_type="image_conversion",
        status="completed",
        progress=100,
        params={},
        task_output={"output_path": "/output/image.png"},
        error_message=None,
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
    )

    async def mock_convert(**kwargs):
        if "on_complete" in kwargs:
            kwargs["on_complete"](job)
        return job

    mock_compute_client.image_conversion.convert = AsyncMock(side_effect=mock_convert)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["compute", "image-conversion", "convert", "--watch", str(temp_image_file), "--format", "png"],
    )

    assert result.exit_code == 0
    mock_compute_client.image_conversion.convert.assert_called_once()
