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
from cl_client.models import JobResponse

from .conftest import parse_cli_json, assert_cli_error


@pytest.mark.integration
class TestMediaThumbnailCLI:
    """Test media thumbnail CLI commands against live services."""

    def test_thumbnail_generate_http_polling(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test media-thumbnail generate with HTTP polling and JSON output."""
        # Execute CLI command with JSON output (uses wait=True by default)
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "media-thumbnail",
                "generate",
                str(test_image),
                "-w", "128",
                "-h", "128",
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "media_thumbnail"

    def test_thumbnail_generate_mqtt_callbacks(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test media-thumbnail generate with MQTT callbacks (--watch flag) and JSON output."""
        # Execute CLI command with --watch for MQTT updates and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "media-thumbnail",
                "generate",
                "--watch",
                str(test_image),
                "-w", "128",
                "-h", "128",
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "media_thumbnail"

    def test_thumbnail_generate_with_output(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
        tmp_path: Path,
    ):
        """Test media-thumbnail generate with output file download and JSON output."""
        output_file = tmp_path / "thumbnail.jpg"

        # Execute CLI command with -o flag to download thumbnail and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "media-thumbnail",
                "generate",
                str(test_image),
                "-w", "128",
                "-h", "128",
                "--output",
                str(output_file),
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "media_thumbnail"
        # Thumbnail file should be downloaded
        assert output_file.exists(), f"Thumbnail file not created at {output_file}"
        assert output_file.stat().st_size > 0, "Thumbnail file is empty"

    def test_thumbnail_generate_invalid_file(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test media-thumbnail generate with missing file returns JSON error."""
        # Execute CLI command with non-existent file and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "media-thumbnail",
                "generate",
                "/nonexistent/file.jpg",
                "-w", "128",
                "-h", "128",
            ],
            env=cli_env,
        )

        # Validate JSON error response
        assert_cli_error(result)
