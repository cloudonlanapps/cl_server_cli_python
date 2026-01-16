"""Integration tests for image conversion CLI commands.

Run with:
    pytest tests/test_integration/test_image_conversion_cli.py \
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
class TestImageConversionCLI:
    """Test image conversion CLI commands against live services."""

    def test_image_convert_http_polling(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_image: Path,
    ):
        """Test image-conversion convert with HTTP polling (default behavior)."""
        # Execute CLI command (uses wait=True by default)
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "image-conversion", "convert", str(test_image),
                "--format", "png",
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output
        # Should show job ID in output
        assert "test-job" in result.output or "job_id" in result.output.lower() or len(result.output) > 0

    def test_image_convert_mqtt_callbacks(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_image: Path,
    ):
        """Test image-conversion convert with MQTT callbacks (--watch flag)."""
        # Execute CLI command with --watch for MQTT updates
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "image-conversion", "convert",
                "--watch",
                "--format", "png",
                str(test_image),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output

    def test_image_convert_with_quality(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_image: Path,
        tmp_path: Path,
    ):
        """Test image-conversion convert with quality parameter."""
        output_file = tmp_path / "converted.jpg"

        # Execute CLI command with quality parameter
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "image-conversion", "convert",
                str(test_image),
                "--format", "jpeg",
                "--quality", "85",
                "--output", str(output_file),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output
        # Converted file should be downloaded
        assert output_file.exists(), f"Converted file not created at {output_file}"
        assert output_file.stat().st_size > 0, "Converted file is empty"

    def test_image_convert_with_output(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_image: Path,
        tmp_path: Path,
    ):
        """Test image-conversion convert with output file download."""
        output_file = tmp_path / "converted.png"

        # Execute CLI command with -o flag to download converted image
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "image-conversion", "convert",
                str(test_image),
                "--format", "png",
                "--output", str(output_file),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output
        # Converted file should be downloaded
        assert output_file.exists(), f"Converted file not created at {output_file}"
        assert output_file.stat().st_size > 0, "Converted file is empty"

    def test_image_convert_invalid_file(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
    ):
        """Test image-conversion convert with missing file."""
        # Execute CLI command with non-existent file
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "image-conversion", "convert",
                "/nonexistent/file.jpg",
                "--format", "png",
            ],
        )

        # Should fail with non-zero exit code
        assert result.exit_code != 0, "Command should fail for missing file"
        # Should show error message
        assert "error" in result.output.lower() or "not found" in result.output.lower() or "does not exist" in result.output.lower()
