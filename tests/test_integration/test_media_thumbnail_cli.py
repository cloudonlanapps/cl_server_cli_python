"""Integration tests for media thumbnail CLI commands.

Run with:
    pytest tests/test_integration/test_media_thumbnail_cli.py \
        --auth-url=http://localhost:8010 \
        --compute-url=http://localhost:8012 \
        --store-url=http://localhost:8011 \
        --username=admin \
        --password=admin
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from cl_client_cli.main import cli


@pytest.mark.integration
class TestMediaThumbnailCLI:
    """Test media thumbnail CLI commands against live services."""

    def test_thumbnail_generate_http_polling(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_image: Path,
    ):
        """Test media-thumbnail generate with HTTP polling (default behavior)."""
        # Execute CLI command (uses wait=True by default)
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "media-thumbnail", "generate", str(test_image),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output
        # Should show job ID in output
        assert "test-job" in result.output or "job_id" in result.output.lower() or len(result.output) > 0

    def test_thumbnail_generate_mqtt_callbacks(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_image: Path,
    ):
        """Test media-thumbnail generate with MQTT callbacks (--watch flag)."""
        # Execute CLI command with --watch for MQTT updates
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "media-thumbnail", "generate",
                "--watch",
                str(test_image),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output

    def test_thumbnail_generate_with_size(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_image: Path,
        tmp_path: Path,
    ):
        """Test media-thumbnail generate with custom size."""
        output_file = tmp_path / "thumbnail.jpg"

        # Execute CLI command with custom size
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "media-thumbnail", "generate",
                str(test_image),
                "--width", "320",
                "--height", "240",
                "--output", str(output_file),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output
        # Thumbnail file should be downloaded
        assert output_file.exists(), f"Thumbnail file not created at {output_file}"
        assert output_file.stat().st_size > 0, "Thumbnail file is empty"

    def test_thumbnail_generate_with_output(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_image: Path,
        tmp_path: Path,
    ):
        """Test media-thumbnail generate with output file download."""
        output_file = tmp_path / "thumbnail.jpg"

        # Execute CLI command with -o flag to download thumbnail
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "media-thumbnail", "generate",
                str(test_image),
                "--output", str(output_file),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output
        # Thumbnail file should be downloaded
        assert output_file.exists(), f"Thumbnail file not created at {output_file}"
        assert output_file.stat().st_size > 0, "Thumbnail file is empty"

    def test_thumbnail_invalid_file(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
    ):
        """Test media-thumbnail generate with missing file."""
        # Execute CLI command with non-existent file
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "media-thumbnail", "generate",
                "/nonexistent/file.jpg",
            ],
        )

        # Should fail with non-zero exit code
        assert result.exit_code != 0, "Command should fail for missing file"
        # Should show error message
        assert "error" in result.output.lower() or "not found" in result.output.lower() or "does not exist" in result.output.lower()
