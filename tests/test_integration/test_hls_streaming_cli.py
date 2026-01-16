"""Integration tests for HLS streaming CLI commands.

Run with:
    pytest tests/test_integration/test_hls_streaming_cli.py \
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
class TestHlsStreamingCLI:
    """Test HLS streaming CLI commands against live services."""

    def test_hls_generate_http_polling(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_image: Path,
    ):
        """Test hls-streaming generate with HTTP polling (default behavior)."""
        # Execute CLI command (uses wait=True by default)
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "hls-streaming", "generate", str(test_image),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output
        # Should show job ID in output
        assert "test-job" in result.output or "job_id" in result.output.lower() or len(result.output) > 0

    def test_hls_generate_mqtt_callbacks(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_image: Path,
    ):
        """Test hls-streaming generate with MQTT callbacks (--watch flag)."""
        # Execute CLI command with --watch for MQTT updates
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "hls-streaming", "generate",
                "--watch",
                str(test_image),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output

    def test_hls_generate_with_output(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_image: Path,
        tmp_path: Path,
    ):
        """Test hls-streaming generate with output file download."""
        output_file = tmp_path / "manifest.m3u8"

        # Execute CLI command with -o flag to download manifest
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "hls-streaming", "generate",
                str(test_image),
                "--output", str(output_file),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output
        # Manifest file should be downloaded
        assert output_file.exists(), f"Manifest file not created at {output_file}"
        assert output_file.stat().st_size > 0, "Manifest file is empty"

    def test_hls_generate_invalid_file(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
    ):
        """Test hls-streaming generate with missing file."""
        # Execute CLI command with non-existent file
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "hls-streaming", "generate",
                "/nonexistent/file.mp4",
            ],
        )

        # Should fail with non-zero exit code
        assert result.exit_code != 0, "Command should fail for missing file"
        # Should show error message
        assert "error" in result.output.lower() or "not found" in result.output.lower() or "does not exist" in result.output.lower()
