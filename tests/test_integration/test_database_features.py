"""Integration tests for CLI database features (jobs, faces, persons, images).

These tests require running services and test the actual CLI commands
against real databases.

Run with:
    pytest tests/test_integration/test_database_features.py \
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

from .conftest import SyncTestHelper


@pytest.mark.integration
class TestJobTracking:
    """Test store jobs command for tracking entity job status."""

    def test_jobs_command_after_upload(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test jobs command shows job status after entity upload."""
        # Create entity with file upload (triggers compute jobs)
        entity_id = test_helper.create_test_entity(
            label="test_jobs_tracking",
            image_path=test_image,
        )

        assert entity_id is not None, "Failed to create entity"

        # Test jobs command - it should query job status immediately
        # No need to wait since we're just checking if the command works
        cli_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "store",
                "jobs",
                str(entity_id),
            ],
        )

        assert cli_result.exit_code == 0, f"CLI failed: {cli_result.output}"
        assert f"Entity Jobs for ID: {entity_id}" in cli_result.output
        assert "Total jobs:" in cli_result.output


@pytest.mark.integration
class TestFaceCommands:
    """Test faces command group (list, similar, download-embedding, matches)."""

    def test_faces_list_command(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test faces list command shows detected faces."""
        # Upload image with faces
        entity_id = test_helper.create_test_entity(
            label="test_faces_list",
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for face detection to complete
        face_id = test_helper.wait_for_faces(entity_id)
        assert face_id is not None, "Face detection did not complete in time"

        # Test faces list command
        cli_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "faces",
                "list",
                str(entity_id),
            ],
        )

        assert cli_result.exit_code == 0, f"CLI failed: {cli_result.output}"
        assert f"Faces in Entity ID: {entity_id}" in cli_result.output
        assert "Total faces:" in cli_result.output

    def test_faces_similar_command(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test faces similar command for face similarity search."""
        # Upload image with face
        entity_id = test_helper.create_test_entity(
            label="test_faces_similar",
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for face detection and embedding
        face_id = test_helper.wait_for_faces(entity_id)
        assert face_id is not None, "Face detection did not complete in time"

        # Test faces similar command
        cli_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "faces",
                "similar",
                str(face_id),
                "--limit",
                "5",
                "--threshold",
                "0.5",
            ],
        )

        assert cli_result.exit_code == 0, f"CLI failed: {cli_result.output}"
        assert f"Similar Faces for Face ID: {face_id}" in cli_result.output
        assert "Found" in cli_result.output
        assert "similar faces" in cli_result.output

    def test_faces_download_embedding(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
        tmp_path: Path,
    ):
        """Test faces download-embedding command."""
        # Upload image with face
        entity_id = test_helper.create_test_entity(
            label="test_faces_download_embedding",
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for face detection and embedding
        face_id = test_helper.wait_for_faces(entity_id)
        assert face_id is not None, "Face detection did not complete in time"

        # Test download-embedding command
        output_file = tmp_path / "face_embedding.npy"
        cli_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "faces",
                "download-embedding",
                str(face_id),
                "--output",
                str(output_file),
            ],
        )

        assert cli_result.exit_code == 0, f"CLI failed: {cli_result.output}"
        assert "Face embedding downloaded" in cli_result.output
        assert output_file.exists(), "Embedding file was not created"
        assert output_file.stat().st_size > 0, "Embedding file is empty"

    def test_faces_matches_command(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test faces matches command for face match history."""
        # Upload image with face
        entity_id = test_helper.create_test_entity(
            label="test_faces_matches",
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for face detection
        face_id = test_helper.wait_for_faces(entity_id)
        assert face_id is not None, "Face detection did not complete in time"

        # Test matches command
        cli_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "faces",
                "matches",
                str(face_id),
            ],
        )

        assert cli_result.exit_code == 0, f"CLI failed: {cli_result.output}"
        assert f"Match History for Face ID: {face_id}" in cli_result.output
        assert "Total matches:" in cli_result.output


@pytest.mark.integration
class TestPersonsCommands:
    """Test persons command group (list, get, update, faces)."""

    def test_persons_list_command(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test persons list command."""
        cli_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "persons",
                "list",
            ],
        )

        assert cli_result.exit_code == 0, f"CLI failed: {cli_result.output}"
        assert "Known Persons" in cli_result.output
        assert "Total persons:" in cli_result.output

    def test_persons_get_update_commands(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test persons get and update commands."""
        # Upload image with face to create a person
        entity_id = test_helper.create_test_entity(
            label="test_persons_update",
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for face detection and person creation
        person_id = test_helper.wait_for_person(entity_id)
        assert person_id is not None, "Person creation did not complete in time"

        # Test persons get command
        cli_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "persons",
                "get",
                str(person_id),
            ],
        )

        assert cli_result.exit_code == 0, f"CLI failed: {cli_result.output}"
        assert f"Person ID: {person_id}" in cli_result.output
        assert "Person Details" in cli_result.output

        # Test persons update command
        cli_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "persons",
                "update",
                str(person_id),
                "--name",
                "Test Person",
            ],
        )

        assert cli_result.exit_code == 0, f"CLI failed: {cli_result.output}"
        assert f"Updated person {person_id}" in cli_result.output
        assert "Test Person" in cli_result.output

    def test_persons_faces_command(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test persons faces command."""
        # Upload image with face
        entity_id = test_helper.create_test_entity(
            label="test_persons_faces",
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for face detection and person creation
        person_id = test_helper.wait_for_person(entity_id)
        assert person_id is not None, "Person creation did not complete in time"

        # Test persons faces command
        cli_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "persons",
                "faces",
                str(person_id),
            ],
        )

        assert cli_result.exit_code == 0, f"CLI failed: {cli_result.output}"
        assert f"Faces for Person ID: {person_id}" in cli_result.output
        assert "Total faces:" in cli_result.output


@pytest.mark.integration
class TestImagesCommands:
    """Test images command group (similar, download-embedding)."""

    def test_images_similar_command(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test images similar command for CLIP-based similarity."""
        # Upload image
        entity_id = test_helper.create_test_entity(
            label="test_images_similar",
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for CLIP embedding to be generated using pysdk's wait_for_job
        clip_ready = test_helper.wait_for_clip_embedding(entity_id)
        assert clip_ready, "CLIP embedding did not complete in time"

        # Test images similar command
        cli_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "images",
                "similar",
                str(entity_id),
                "--limit",
                "5",
                "--threshold",
                "0.8",
            ],
        )

        assert cli_result.exit_code == 0, f"CLI failed: {cli_result.output}"
        assert f"Similar Images for Entity ID: {entity_id}" in cli_result.output
        assert "Found" in cli_result.output
        assert "similar images" in cli_result.output

    def test_images_similar_with_details(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test images similar command with --details flag."""
        # Upload image
        entity_id = test_helper.create_test_entity(
            label="test_images_similar_details",
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for CLIP embedding using pysdk's wait_for_job
        clip_ready = test_helper.wait_for_clip_embedding(entity_id)
        assert clip_ready, "CLIP embedding did not complete in time"

        # Test images similar with details
        cli_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "images",
                "similar",
                str(entity_id),
                "--details",
            ],
        )

        assert cli_result.exit_code == 0, f"CLI failed: {cli_result.output}"
        assert f"Similar Images for Entity ID: {entity_id}" in cli_result.output

    def test_images_download_embedding(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
        tmp_path: Path,
    ):
        """Test images download-embedding command."""
        # Upload image
        entity_id = test_helper.create_test_entity(
            label="test_images_download_embedding",
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for CLIP embedding using pysdk's wait_for_job
        clip_ready = test_helper.wait_for_clip_embedding(entity_id)
        assert clip_ready, "CLIP embedding did not complete in time"

        # Test download-embedding command
        output_file = tmp_path / "clip_embedding.npy"
        cli_result = cli_runner.invoke(
            cli,
            [
                "--username",
                cli_env["CL_USERNAME"],
                "--password",
                cli_env["CL_PASSWORD"],
                "--auth-url",
                cli_env["CL_AUTH_URL"],
                "--store-url",
                cli_env["CL_STORE_URL"],
                "images",
                "download-embedding",
                str(entity_id),
                "--output",
                str(output_file),
            ],
        )

        assert cli_result.exit_code == 0, f"CLI failed: {cli_result.output}"
        assert "Entity CLIP embedding downloaded" in cli_result.output
        assert output_file.exists(), "Embedding file was not created"
        assert output_file.stat().st_size > 0, "Embedding file is empty"
