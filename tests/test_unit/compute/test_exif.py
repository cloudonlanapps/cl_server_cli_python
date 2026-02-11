"""Unit tests for EXIF commands."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client.models import JobResponse
from cl_client_cli.main import cli

def test_extract_polling_mode(mock_compute_client, temp_image_file):
    """Test exif extract in polling mode."""
    # Configure mock
    job = JobResponse(
        job_id="test-job-789",
        task_type="exif",
        status="completed",
        progress=100,
        params={},
        task_output={
            "make": "Canon",
            "model": "EOS 5D Mark IV",
            "datetime": "2024:01:15 10:30:00",
        },
        error_message=None,
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
    )
    mock_compute_client.exif.extract = AsyncMock(return_value=job)

    # Run command
    runner = CliRunner()
    result = runner.invoke(cli, ["compute", "exif", "extract", str(temp_image_file)])

    # Verify
    assert result.exit_code == 0
    assert "Canon" in result.output
    assert "EOS 5D Mark IV" in result.output
    mock_compute_client.exif.extract.assert_called_once()

def test_exif_watch_mode(mock_compute_client, temp_image_file):
    """Test exif extract with watch mode."""
    job = JobResponse(
        job_id="test-job-exif-watch",
        task_type="exif",
        status="completed",
        progress=100,
        params={},
        task_output={"make": "Canon", "model": "EOS 5D"},
        error_message=None,
        priority=5,
        created_at=1234567890000,
        updated_at=1234567890000,
    )

    async def mock_extract(**kwargs):
        if "on_complete" in kwargs:
            kwargs["on_complete"](job)
        return job

    mock_compute_client.exif.extract = AsyncMock(side_effect=mock_extract)

    runner = CliRunner()
    result = runner.invoke(cli, ["compute", "exif", "extract", "--watch", str(temp_image_file)])

    assert result.exit_code == 0
    mock_compute_client.exif.extract.assert_called_once()
