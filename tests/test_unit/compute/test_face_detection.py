"""Unit tests for face detection commands."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client_cli.main import cli

def test_detect_polling_mode(mock_compute_client, temp_image_file, completed_job, mandatory_args):
    """Test face-detection detect in polling mode."""
    # Configure mock
    completed_job.task_type = "face_detection"
    completed_job.task_output = {"faces": [{"bbox": [0, 0, 100, 100], "confidence": 0.99}]}
    mock_compute_client.face_detection.detect = AsyncMock(return_value=completed_job)

    # Run command
    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["compute", "face-detection", "detect", str(temp_image_file)])

    # Verify
    assert result.exit_code == 0
    assert "test-job-123" in result.output
    assert "completed" in result.output.lower()
    mock_compute_client.face_detection.detect.assert_called_once()

def test_detect_watch_mode(mock_compute_client, temp_image_file, completed_job, mandatory_args):
    """Test face-detection detect with --watch flag."""
    # Configure mock to simulate immediate completion via callback
    completed_job.task_type = "face_detection"
    completed_job.task_output = {"faces": [{"bbox": [0, 0, 100, 100], "confidence": 0.99}]}

    async def mock_detect(**kwargs):
        # Simulate immediate callback
        if "on_complete" in kwargs:
            kwargs["on_complete"](completed_job)
        return completed_job

    mock_compute_client.face_detection.detect = AsyncMock(side_effect=mock_detect)

    # Run command
    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["compute", "face-detection", "detect", "--watch", str(temp_image_file)])

    # Verify
    assert result.exit_code == 0
    mock_compute_client.face_detection.detect.assert_called_once()

def test_detect_missing_file(mock_compute_client, mandatory_args):
    """Test face-detection detect with missing file."""
    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["compute", "face-detection", "detect", "/nonexistent/file.jpg"])

    # Should fail validation before calling API
    assert result.exit_code != 0
