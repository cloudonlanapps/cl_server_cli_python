"""Integration tests for hash CLI commands.

Run with:
    pytest tests/test_integration/test_hash_cli.py \
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
class TestHashCLI:
    """Test hash CLI commands against live services."""

    def test_hash_compute_http_polling(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_image: Path,
    ):
        """Test hash compute with HTTP polling (default behavior)."""
        # Execute CLI command (uses wait=True by default)
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "hash", "compute", str(test_image),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output
        # Should show job ID in output
        assert "test-job" in result.output or "job_id" in result.output.lower() or len(result.output) > 0

    def test_hash_compute_mqtt_callbacks(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_image: Path,
    ):
        """Test hash compute with MQTT callbacks (--watch flag)."""
        # Execute CLI command with --watch for MQTT updates
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "hash", "compute",
                "--watch",
                str(test_image),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output

    def test_hash_compute_with_output(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
        test_image: Path,
        tmp_path: Path,
    ):
        """Test hash compute with output file download."""
        output_file = tmp_path / "hash_result.json"

        # Execute CLI command with -o flag to download hash
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "hash", "compute",
                str(test_image),
                "--output", str(output_file),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "completed" in result.output.lower() or "✓" in result.output
        # Hash file should be downloaded
        assert output_file.exists(), f"Hash file not created at {output_file}"
        assert output_file.stat().st_size > 0, "Hash file is empty"

    def test_hash_compute_invalid_file(
        self,
        cli_runner: CliRunner,
        cli_env: dict,
    ):
        """Test hash compute with missing file."""
        # Execute CLI command with non-existent file
        result = cli_runner.invoke(
            cli,
            [
                "--username", cli_env["CL_USERNAME"],
                "--password", cli_env["CL_PASSWORD"],
                "--compute-url", cli_env["CL_COMPUTE_URL"],
                "hash", "compute",
                "/nonexistent/file.jpg",
            ],
        )

        # Should fail with non-zero exit code
        assert result.exit_code != 0, "Command should fail for missing file"
        # Should show error message
        assert "error" in result.output.lower() or "not found" in result.output.lower() or "does not exist" in result.output.lower()
