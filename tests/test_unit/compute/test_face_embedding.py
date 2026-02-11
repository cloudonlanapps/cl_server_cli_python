"""Unit tests for face embedding commands."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client_cli.main import cli

def test_embed_polling_mode(mock_compute_client, temp_image_file, completed_job, mandatory_args):
    """Test face-embedding embed in polling mode."""
    # Configure mock
    completed_job.task_type = "face_embedding"
    completed_job.task_output = {"embeddings": [[0.1] * 512]}
    mock_compute_client.face_embedding.embed_faces = AsyncMock(return_value=completed_job)

    # Run command
    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["compute", "face-embedding", "embed", str(temp_image_file)])

    # Verify
    assert result.exit_code == 0
    assert "test-job-123" in result.output
    assert "completed" in result.output.lower()
    mock_compute_client.face_embedding.embed_faces.assert_called_once()

def test_embed_watch_mode(mock_compute_client, temp_image_file, completed_job, mandatory_args):
    """Test face-embedding embed with --watch flag."""
    # Configure mock to simulate immediate completion via callback
    completed_job.task_type = "face_embedding"
    completed_job.task_output = {"embeddings": [[0.1] * 512]}

    async def mock_embed(**kwargs):
        # Simulate immediate callback
        if "on_complete" in kwargs:
            kwargs["on_complete"](completed_job)
        return completed_job

    mock_compute_client.face_embedding.embed_faces = AsyncMock(side_effect=mock_embed)

    # Run command
    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["compute", "face-embedding", "embed", "--watch", str(temp_image_file)])

    # Verify
    assert result.exit_code == 0
    mock_compute_client.face_embedding.embed_faces.assert_called_once()

def test_embed_missing_file(mock_compute_client, mandatory_args):
    """Test face-embedding embed with missing file."""
    runner = CliRunner()
    result = runner.invoke(cli, mandatory_args + ["compute", "face-embedding", "embed", "/nonexistent/file.jpg"])

    # Should fail validation before calling API
    assert result.exit_code != 0
