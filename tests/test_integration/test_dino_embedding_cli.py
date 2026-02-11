"""Integration tests for DINO embedding CLI commands.

Run with:
    pytest tests/test_integration/test_dino_embedding_cli.py \
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
class TestDinoEmbeddingCLI:
    """Test DINO embedding CLI commands against live services."""

    def test_dino_embed_http_polling(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
        mandatory_args: list[str],
    ):
        """Test dino-embedding embed with HTTP polling and JSON output."""
        # Execute CLI command with JSON output (uses wait=True by default)
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--json",
                "compute", "dino-embedding",
                "embed",
                str(test_image),
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "dino_embedding"

    def test_dino_embed_mqtt_callbacks(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
        mandatory_args: list[str],
    ):
        """Test dino-embedding embed with MQTT callbacks (--watch flag) and JSON output."""
        # Execute CLI command with --watch for MQTT updates and JSON output
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--json",
                "compute", "dino-embedding",
                "embed",
                "--watch",
                str(test_image),
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "dino_embedding"

    def test_dino_embed_with_output(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_image: Path,
        tmp_path: Path,
        mandatory_args: list[str],
    ):
        """Test dino-embedding embed with output file download and JSON output."""
        output_file = tmp_path / "dino_embedding.npy"

        # Execute CLI command with -o flag to download embedding and JSON output
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--json",
                "compute", "dino-embedding",
                "embed",
                str(test_image),
                "--output",
                str(output_file),
            ],
            env=cli_env,
        )

        # Parse and validate with SDK JobResponse model
        job = parse_cli_json(result, JobResponse)
        assert job.status == "completed"
        assert job.task_type == "dino_embedding"
        # Embedding file should be downloaded
        assert output_file.exists(), f"Embedding file not created at {output_file}"
        assert output_file.stat().st_size > 0, "Embedding file is empty"

    def test_dino_embed_invalid_file(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        mandatory_args: list[str],
    ):
        """Test dino-embedding embed with missing file returns JSON error."""
        # Execute CLI command with non-existent file and JSON output
        result = cli_runner.invoke(
            cli,
            mandatory_args
            + [
                "--json",
                "compute", "dino-embedding",
                "embed",
                "/nonexistent/file.jpg",
            ],
            env=cli_env,
        )

        # Validate JSON error response
        assert_cli_error(result)
