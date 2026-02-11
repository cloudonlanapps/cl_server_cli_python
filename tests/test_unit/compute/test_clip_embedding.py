"""Unit tests for CLIP embedding commands."""

from unittest.mock import AsyncMock
from click.testing import CliRunner
from cl_client_cli.main import cli

def test_embed_polling_mode(mock_compute_client, temp_image_file, completed_job):
    """Test clip-embedding embed in polling mode."""
    # Configure mock
    mock_compute_client.clip_embedding.embed_image = AsyncMock(return_value=completed_job)

    # Run command
    runner = CliRunner()
    result = runner.invoke(cli, ["compute", "clip-embedding", "embed", str(temp_image_file)])

    # Verify
    assert result.exit_code == 0
    assert "test-job-123" in result.output
    assert "completed" in result.output.lower()
    mock_compute_client.clip_embedding.embed_image.assert_called_once()

def test_embed_watch_mode(mock_compute_client, temp_image_file, completed_job):
    """Test clip-embedding embed with --watch flag."""
    # Configure mock to simulate immediate completion via callback
    async def mock_embed_image(**kwargs):
        # Simulate immediate callback
        if "on_complete" in kwargs:
            kwargs["on_complete"](completed_job)
        return completed_job

    mock_compute_client.clip_embedding.embed_image = AsyncMock(side_effect=mock_embed_image)

    # Run command
    runner = CliRunner()
    result = runner.invoke(cli, ["compute", "clip-embedding", "embed", "--watch", str(temp_image_file)])

    # Verify
    assert result.exit_code == 0
    mock_compute_client.clip_embedding.embed_image.assert_called_once()

def test_embed_missing_file(mock_compute_client):
    """Test clip-embedding embed with missing file."""
    runner = CliRunner()
    result = runner.invoke(cli, ["compute", "clip-embedding", "embed", "/nonexistent/file.jpg"])

    # Should fail validation before calling API
    assert result.exit_code != 0
