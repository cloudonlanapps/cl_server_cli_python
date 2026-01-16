"""Integration tests for face detection CLI commands.

Run with:
    pytest tests/test_integration/test_face_detection_cli.py \
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
class TestFaceDetectionCLI:
    """Test face detection CLI commands against live services."""

    def test_face_detect_http_polling(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test face-detection detect with HTTP polling and JSON output."""
        # Execute CLI command with JSON output (uses wait=True by default)
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "face-detection",
                "detect",
                str(test_image),
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "face_detection"

    def test_face_detect_mqtt_callbacks(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
    ):
        """Test face-detection detect with MQTT callbacks (--watch flag) and JSON output."""
        # Execute CLI command with --watch for MQTT updates and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "face-detection",
                "detect",
                "--watch",
                str(test_image),
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "face_detection"

    def test_face_detect_with_output(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
        tmp_path: Path,
    ):
        """Test face-detection detect with output file download and JSON output."""
        output_file = tmp_path / "faces.json"

        # Execute CLI command with -o flag to download result and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "face-detection",
                "detect",
                str(test_image),
                "--output",
                str(output_file),
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "face_detection"
        # Output file should be downloaded
        assert output_file.exists(), f"Output file not created at {output_file}"
        assert output_file.stat().st_size > 0, "Output file is empty"

    def test_face_detect_invalid_file(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test face-detection detect with missing file returns JSON error."""
        # Execute CLI command with non-existent file and JSON output
        result = cli_runner.invoke(
            cli,
            [
                "--json",
                "face-detection",
                "detect",
                "/nonexistent/file.jpg",
            ],
            env=cli_env,
        )

        # Validate JSON error response
        assert_cli_error(result)
