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
from cl_client.models import JobResponse
from tests.conftest import parse_cli_json, assert_cli_error


@pytest.mark.integration
class TestImageConversionCLI:
    """Test image conversion CLI commands against live services."""

    def test_image_convert_http_polling(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test image-conversion convert with HTTP polling and JSON output."""
        # Execute CLI command with JSON output (uses wait=True by default)
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "compute", "image-conversion",
                "convert",
                str(test_image),
                "--format",
                "png",
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "image_conversion"

    def test_image_convert_mqtt_callbacks(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test image-conversion convert with MQTT callbacks (--watch flag) and JSON output."""
        # Execute CLI command with --watch for MQTT updates and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "compute", "image-conversion",
                "convert",
                "--watch",
                str(test_image),
                "--format",
                "png",
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "image_conversion"

    def test_image_convert_with_output(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
        tmp_path: Path,
    ):
        """Test image-conversion convert with output file download and JSON output."""
        output_file = tmp_path / "converted.png"

        # Execute CLI command with -o flag to download converted image and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "compute", "image-conversion",
                "convert",
                str(test_image),
                "--format",
                "png",
                "--output",
                str(output_file),
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "image_conversion"
        # Output file should be downloaded
        assert output_file.exists(), f"Output file not created at {output_file}"
        assert output_file.stat().st_size > 0, "Output file is empty"

    def test_image_convert_invalid_file(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test image-conversion convert with missing file returns JSON error."""
        # Execute CLI command with non-existent file and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "compute", "image-conversion",
                "convert",
                "/nonexistent/file.jpg",
                "--format",
                "png",
            ],
            env=cli_env,
        )

        # Validate JSON error response
        assert_cli_error(result)

    def test_image_convert_different_format(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test image-conversion convert with different target format and JSON output."""
        # Execute CLI command with webp format and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "compute", "image-conversion",
                "convert",
                str(test_image),
                "--format",
                "webp",
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "image_conversion"
