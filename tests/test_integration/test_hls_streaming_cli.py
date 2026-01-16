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
from cl_client.models import JobResponse

from .conftest import parse_cli_json, assert_cli_error


@pytest.mark.integration
class TestHlsStreamingCLI:
    """Test HLS streaming CLI commands against live services."""

    def test_hls_generate_http_polling(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test hls-streaming generate with HTTP polling and JSON output."""
        # Execute CLI command with JSON output (uses wait=True by default)
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "hls-streaming",
                "generate-manifest",
                str(test_image),
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "hls_streaming"

    def test_hls_generate_mqtt_callbacks(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test hls-streaming generate with MQTT callbacks (--watch flag) and JSON output."""
        # Execute CLI command with --watch for MQTT updates and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "hls-streaming",
                "generate-manifest",
                "--watch",
                str(test_image),
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "hls_streaming"

    def test_hls_generate_with_output(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
        tmp_path: Path,
    ):
        """Test hls-streaming generate with output file download and JSON output."""
        output_file = tmp_path / "manifest.m3u8"

        # Execute CLI command with -o flag to download manifest and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "hls-streaming",
                "generate-manifest",
                str(test_image),
                "--output",
                str(output_file),
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "hls_streaming"
        # Output file should be downloaded
        assert output_file.exists(), f"Output file not created at {output_file}"
        assert output_file.stat().st_size > 0, "Output file is empty"

    def test_hls_generate_invalid_file(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test hls-streaming generate with missing file returns JSON error."""
        # Execute CLI command with non-existent file and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "hls-streaming",
                "generate-manifest",
                "/nonexistent/file.mp4",
            ],
            env=cli_env,
        )

        # Validate JSON error response
        assert_cli_error(result)
