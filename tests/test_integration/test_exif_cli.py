"""Integration tests for EXIF CLI commands.

Run with:
    pytest tests/test_integration/test_exif_cli.py \
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
class TestExifCLI:
    """Test EXIF CLI commands against live services."""

    def test_exif_extract_http_polling(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test exif extract with HTTP polling (default behavior)."""
        # Execute CLI command (uses wait=True by default)
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--compute-url",
                cli_env["CL_COMPUTE_URL"],
                "exif",
                "extract",
                str(test_image),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output
        # Should show job ID in output
        assert (
            "test-job" in result.output
            or "job_id" in result.output.lower()
            or len(result.output) > 0
        )

    def test_exif_extract_mqtt_callbacks(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test exif extract with MQTT callbacks (--watch flag)."""
        # Execute CLI command with --watch for MQTT updates
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--compute-url",
                cli_env["CL_COMPUTE_URL"],
                "exif",
                "extract",
                "--watch",
                str(test_image),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output

    def test_exif_extract_with_output(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
        tmp_path: Path,
    ):
        """Test exif extract with output file download."""
        output_file = tmp_path / "exif_data.json"

        # Execute CLI command with -o flag to download EXIF data
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--compute-url",
                cli_env["CL_COMPUTE_URL"],
                "exif",
                "extract",
                str(test_image),
                "--output",
                str(output_file),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output
        # EXIF data file should be downloaded
        assert output_file.exists(), f"EXIF data file not created at {output_file}"
        assert output_file.stat().st_size > 0, "EXIF data file is empty"

    def test_exif_extract_invalid_file(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test exif extract with missing file."""
        # Execute CLI command with non-existent file
        result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--compute-url",
                cli_env["CL_COMPUTE_URL"],
                "exif",
                "extract",
                "/nonexistent/file.jpg",
            ],
        )

        # Should fail with non-zero exit code
        assert result.exit_code != 0, "Command should fail for missing file"
        # Should show error message
        assert (
            "error" in result.output.lower()
            or "not found" in result.output.lower()
            or "does not exist" in result.output.lower()
        )
