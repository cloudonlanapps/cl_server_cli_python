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

import uuid
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from cl_client_cli.main import cli
from cl_client.store_client import (
    FaceResponse,
    KnownPersonResponse,
    SimilarFacesResponse,
    SimilarImagesResponse,
    FaceMatchResult,
    EntityJobResponse,
)

from .conftest import SyncTestHelper, parse_cli_json, parse_cli_json_list, assert_cli_success


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
        """Test jobs command shows job status after entity upload with JSON output."""
        label = f"test_jobs_tracking_{uuid.uuid4().hex[:8]}"
        # Create entity with file upload (triggers compute jobs)
        entity_id = test_helper.create_test_entity(
            label=label,
            image_path=test_image,
        )

        assert entity_id is not None, "Failed to create entity"

        # Test jobs command with JSON output
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
                "--json",
                "store",
                "jobs",
                str(entity_id),
            ],
        )

        # Parse and validate with SDK EntityJobResponse model list
        jobs = parse_cli_json_list(cli_result, EntityJobResponse)
        assert len(jobs) > 0
        assert all(j.entity_id == entity_id for j in jobs)


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
        """Test faces list command shows detected faces with JSON output."""
        label = f"test_faces_list_{uuid.uuid4().hex[:8]}"
        # Upload image with faces
        entity_id = test_helper.create_test_entity(
            label=label,
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for face detection to complete
        face_id = test_helper.wait_for_faces(entity_id)
        assert face_id is not None, "Face detection did not complete in time"

        # Test faces list command with JSON output
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
                "--json",
                "faces",
                "list",
                str(entity_id),
            ],
        )

        # Parse list of FaceResponse models
        faces = parse_cli_json_list(cli_result, FaceResponse)
        assert len(faces) > 0
        assert faces[0].entity_id == entity_id

    def test_faces_similar_command(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test faces similar command for face similarity search with JSON output."""
        label = f"test_faces_similar_{uuid.uuid4().hex[:8]}"
        # Upload image with face
        entity_id = test_helper.create_test_entity(
            label=label,
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for face detection and embedding
        face_id = test_helper.wait_for_faces(entity_id)
        assert face_id is not None, "Face detection did not complete in time"

        # Test faces similar command with JSON output (with retries for indexing)
        cli_result = None
        for i in range(5):
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
                    "--json",
                    "faces",
                    "similar",
                    str(face_id),
                    "--limit",
                    "5",
                    "--threshold",
                    "0.5",
                ],
            )
            if cli_result.exit_code == 0:
                break
            time.sleep(2)

        # Parse and validate with SDK SimilarFacesResponse model
        response = parse_cli_json(cli_result, SimilarFacesResponse)
        assert hasattr(response, "results")
        assert isinstance(response.results, list)

    def test_faces_download_embedding(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
        tmp_path: Path,
    ):
        """Test faces download-embedding command with JSON output."""
        label = f"test_faces_download_{uuid.uuid4().hex[:8]}"
        # Upload image with face
        entity_id = test_helper.create_test_entity(
            label=label,
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for face detection and embedding
        face_id = test_helper.wait_for_faces(entity_id)
        assert face_id is not None, "Face detection did not complete in time"

        # Test download-embedding command with JSON output (with retries)
        output_file = tmp_path / "face_embedding.npy"
        cli_result = None
        for i in range(5):
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
                    "--json",
                    "faces",
                    "download-embedding",
                    str(face_id),
                    "--output",
                    str(output_file),
                ],
            )
            if cli_result.exit_code == 0:
                break
            time.sleep(2)

        # Validate success response
        assert_cli_success(cli_result, "Face embedding downloaded")
        assert output_file.exists(), "Embedding file was not created"
        assert output_file.stat().st_size > 0, "Embedding file is empty"

    def test_faces_matches_command(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test faces matches command for face match history with JSON output."""
        label = f"test_faces_matches_{uuid.uuid4().hex[:8]}"
        # Upload image with face
        entity_id = test_helper.create_test_entity(
            label=label,
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for face detection
        face_id = test_helper.wait_for_faces(entity_id)
        assert face_id is not None, "Face detection did not complete in time"

        # Test matches command with JSON output
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
                "--json",
                "faces",
                "matches",
                str(face_id),
            ],
        )

        # Parse list of FaceMatchResult models
        matches = parse_cli_json_list(cli_result, FaceMatchResult)
        assert isinstance(matches, list)
        # May be empty if no matches yet


@pytest.mark.integration
class TestPersonsCommands:
    """Test persons command group (list, get, update, faces)."""

    def test_persons_list_command(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
    ):
        """Test persons list command with JSON output."""
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
                "--json",
                "persons",
                "list",
            ],
        )

        # Parse list of KnownPersonResponse models
        persons = parse_cli_json_list(cli_result, KnownPersonResponse)
        assert isinstance(persons, list)
        # May be empty if no persons yet

    def test_persons_get_update_commands(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test persons get and update commands with JSON output."""
        label = f"test_persons_update_{uuid.uuid4().hex[:8]}"
        # Upload image with face to create a person
        entity_id = test_helper.create_test_entity(
            label=label,
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for face detection and person creation
        person_id = test_helper.wait_for_person(entity_id)
        assert person_id is not None, "Person creation did not complete in time"

        # Test persons get command with JSON output
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
                "--json",
                "persons",
                "get",
                str(person_id),
            ],
        )

        # Parse and validate with SDK KnownPersonResponse model
        person = parse_cli_json(cli_result, KnownPersonResponse)
        assert person.id == person_id

        # Test persons update command with JSON output
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
                "--json",
                "persons",
                "update",
                str(person_id),
                "--name",
                "Test Person",
            ],
        )

        # Parse updated person
        updated_person = parse_cli_json(cli_result, KnownPersonResponse)
        assert updated_person.id == person_id
        assert updated_person.name == "Test Person"

    def test_persons_faces_command(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test persons faces command with JSON output."""
        label = f"test_persons_faces_{uuid.uuid4().hex[:8]}"
        # Upload image with face
        entity_id = test_helper.create_test_entity(
            label=label,
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for face detection and person creation
        person_id = test_helper.wait_for_person(entity_id)
        assert person_id is not None, "Person creation did not complete in time"

        # Test persons faces command with JSON output
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
                "--json",
                "persons",
                "faces",
                str(person_id),
            ],
        )

        # Parse list of FaceResponse models
        faces = parse_cli_json_list(cli_result, FaceResponse)
        assert len(faces) > 0
        # All faces should belong to this person
        for face in faces:
            assert face.known_person_id == person_id


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
        """Test images similar command for CLIP-based similarity with JSON output."""
        label = f"test_images_similar_{uuid.uuid4().hex[:8]}"
        # Upload image
        entity_id = test_helper.create_test_entity(
            label=label,
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for CLIP embedding to be generated using pysdk's wait_for_job
        clip_ready = test_helper.wait_for_clip_embedding(entity_id)
        assert clip_ready, "CLIP embedding did not complete in time"

        # Test images similar command with JSON output (with retries for indexing)
        cli_result = None
        for i in range(5):
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
                    "--json",
                    "images",
                    "similar",
                    str(entity_id),
                    "--limit",
                    "5",
                    "--threshold",
                    "0.5",
                ],
            )
            if cli_result.exit_code == 0:
                break
            time.sleep(2)

        # Parse and validate with SDK SimilarImagesResponse model
        response = parse_cli_json(cli_result, SimilarImagesResponse)
        assert hasattr(response, "results")
        assert isinstance(response.results, list)

    def test_images_similar_with_details(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
    ):
        """Test images similar command with --details flag and JSON output."""
        label = f"test_images_similar_det_{uuid.uuid4().hex[:8]}"
        # Upload image
        entity_id = test_helper.create_test_entity(
            label=label,
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for CLIP embedding using pysdk's wait_for_job
        clip_ready = test_helper.wait_for_clip_embedding(entity_id)
        assert clip_ready, "CLIP embedding did not complete in time"

        # Test images similar with details command with JSON output (with retries)
        cli_result = None
        for i in range(5):
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
                    "--json",
                    "images",
                    "similar",
                    str(entity_id),
                    "--details",
                ],
            )
            if cli_result.exit_code == 0:
                break
            time.sleep(2)

        # Parse and validate with SDK SimilarImagesResponse model
        response = parse_cli_json(cli_result, SimilarImagesResponse)
        assert hasattr(response, "results")
        assert isinstance(response.results, list)

    def test_images_download_embedding(
        self,
        cli_runner: CliRunner,
        cli_env: dict[str, str],
        test_helper: SyncTestHelper,
        test_image: Path,
        tmp_path: Path,
    ):
        """Test images download-embedding command with JSON output."""
        label = f"test_images_download_{uuid.uuid4().hex[:8]}"
        # Upload image
        entity_id = test_helper.create_test_entity(
            label=label,
            image_path=test_image,
        )

        assert entity_id is not None

        # Wait for CLIP embedding using pysdk's wait_for_job
        clip_ready = test_helper.wait_for_clip_embedding(entity_id)
        assert clip_ready, "CLIP embedding did not complete in time"

        # Test download-embedding command with JSON output
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
                "--json",
                "images",
                "download-embedding",
                str(entity_id),
                "--output",
                str(output_file),
            ],
        )

        # Validate success response
        assert_cli_success(cli_result, "Entity CLIP embedding downloaded")
        assert output_file.exists(), "Embedding file was not created"
        assert output_file.stat().st_size > 0, "Embedding file is empty"
