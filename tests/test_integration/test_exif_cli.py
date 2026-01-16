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
from cl_client.models import JobResponse

from .conftest import parse_cli_json, assert_cli_error


@pytest.mark.integration
class TestExifCLI:
    """Test EXIF CLI commands against live services."""

    def test_exif_extract_http_polling(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test exif extract with HTTP polling and JSON output."""
        # Execute CLI command with JSON output (uses wait=True by default)
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "exif",
                "extract",
                str(test_image),
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "exif"

    def test_exif_extract_mqtt_callbacks(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test exif extract with MQTT callbacks (--watch flag) and JSON output."""
        # Execute CLI command with --watch for MQTT updates and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "exif",
                "extract",
                "--watch",
                str(test_image),
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "exif"

    def test_exif_extract_with_output(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
        tmp_path: Path,
    ):
        """Test exif extract with output file download and JSON output."""
        output_file = tmp_path / "exif.json"

        # Execute CLI command with -o flag to download result and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "exif",
                "extract",
                str(test_image),
                "--output",
                str(output_file),
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "exif"
        # Output file should be downloaded
        assert output_file.exists(), f"Output file not created at {output_file}"
        assert output_file.stat().st_size > 0, "Output file is empty"

    def test_exif_extract_invalid_file(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test exif extract with missing file returns JSON error."""
        # Execute CLI command with non-existent file and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "exif",
                "extract",
                "/nonexistent/file.jpg",
            ],
            env=cli_env,
        )

        # Validate JSON error response
        assert_cli_error(result)
