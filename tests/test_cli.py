"""Unit tests for CLI commands."""

from unittest.mock import AsyncMock
import pytest
import json

from click.testing import CliRunner

from cl_client.models import JobResponse
from cl_client.store_models import (
    Entity,
    EntityListResponse,
    StorePref,
    StoreOperationResult,
    AuditReport,
    CleanupReport,
)
from cl_client.intelligence_models import EntityIntelligenceData
from cl_client_cli.main import cli


class TestClipEmbedding:
    """Tests for clip-embedding commands."""

    def test_embed_polling_mode(self, mock_compute_client, temp_image_file, completed_job, mandatory_args):
        """Test clip-embedding embed in polling mode."""
        # Configure mock
        mock_compute_client.clip_embedding.embed_image = AsyncMock(return_value=completed_job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["clip-embedding", "embed", str(temp_image_file)])

        # Verify
        assert result.exit_code == 0
        assert "test-job-123" in result.output
        assert "completed" in result.output.lower()
        mock_compute_client.clip_embedding.embed_image.assert_called_once()

    def test_embed_watch_mode(self, mock_compute_client, temp_image_file, completed_job, mandatory_args):
        """Test clip-embedding embed with --watch flag."""
        # Configure mock to simulate immediate completion via callback
        async def mock_embed_image(**kwargs):
            # Simulate immediate callback
            if "on_complete" in kwargs:
                kwargs["on_complete"](completed_job)
            return completed_job

        mock_compute_client.clip_embedding.embed_image = AsyncMock(side_effect=mock_embed_image)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["clip-embedding", "embed", "--watch", str(temp_image_file)])

        # Verify
        assert result.exit_code == 0
        mock_compute_client.clip_embedding.embed_image.assert_called_once()

    def test_embed_missing_file(self, mock_compute_client, mandatory_args):
        """Test clip-embedding embed with missing file."""
        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["clip-embedding", "embed", "/nonexistent/file.jpg"])

        # Should fail validation before calling API
        assert result.exit_code != 0


class TestDinoEmbedding:
    """Tests for dino-embedding commands."""

    def test_embed_polling_mode(self, mock_compute_client, temp_image_file, completed_job, mandatory_args):
        """Test dino-embedding embed in polling mode."""
        # Configure mock
        job = JobResponse(
            job_id="test-job-456",
            task_type="dino_embedding",
            status="completed",
            progress=100,
            params={},
            task_output={"embedding": [0.1] * 384},
            error_message=None,
            priority=5,
            created_at=1234567890000,
            updated_at=1234567890000,
        )
        mock_compute_client.dino_embedding.embed_image = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["dino-embedding", "embed", str(temp_image_file)])

        # Verify
        assert result.exit_code == 0
        assert "test-job-456" in result.output
        mock_compute_client.dino_embedding.embed_image.assert_called_once()


class TestExif:
    """Tests for exif commands."""

    def test_extract_polling_mode(self, mock_compute_client, temp_image_file, mandatory_args):
        """Test exif extract in polling mode."""
        # Configure mock
        job = JobResponse(
            job_id="test-job-789",
            task_type="exif",
            status="completed",
            progress=100,
            params={},
            task_output={
                "make": "Canon",
                "model": "EOS 5D Mark IV",
                "datetime": "2024:01:15 10:30:00",
            },
            error_message=None,
            priority=5,
            created_at=1234567890000,
            updated_at=1234567890000,
        )
        mock_compute_client.exif.extract = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["exif", "extract", str(temp_image_file)])

        # Verify
        assert result.exit_code == 0
        assert "Canon" in result.output
        assert "EOS 5D Mark IV" in result.output
        mock_compute_client.exif.extract.assert_called_once()


class TestHash:
    """Tests for hash commands."""

    def test_compute_polling_mode(self, mock_compute_client, temp_image_file, mandatory_args):
        """Test hash compute in polling mode."""
        # Configure mock
        job = JobResponse(
            job_id="test-job-ghi",
            task_type="hash",
            status="completed",
            progress=100,
            params={},
            task_output={
                "phash": "abcdef1234567890",
                "dhash": "fedcba0987654321",
            },
            error_message=None,
            priority=5,
            created_at=1234567890000,
            updated_at=1234567890000,
        )
        mock_compute_client.hash.compute = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["hash", "compute", str(temp_image_file)])

        # Verify
        assert result.exit_code == 0
        assert "abcdef1234567890" in result.output
        assert "fedcba0987654321" in result.output
        mock_compute_client.hash.compute.assert_called_once()


class TestHlsStreaming:
    """Tests for hls-streaming commands."""

    def test_generate_manifest_polling_mode(self, mock_compute_client, temp_video_file, mandatory_args):
        """Test hls-streaming generate-manifest in polling mode."""
        # Configure mock
        job = JobResponse(
            job_id="test-job-jkl",
            task_type="hls_streaming",
            status="completed",
            progress=100,
            params={},
            task_output={
                "manifest_url": "/output/manifest.m3u8",
                "segments": 10,
            },
            error_message=None,
            priority=5,
            created_at=1234567890000,
            updated_at=1234567890000,
        )
        mock_compute_client.hls_streaming.generate_manifest = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["hls-streaming", "generate-manifest", str(temp_video_file)])

        # Verify
        assert result.exit_code == 0
        assert "manifest.m3u8" in result.output
        mock_compute_client.hls_streaming.generate_manifest.assert_called_once()


class TestImageConversion:
    """Tests for image-conversion commands."""

    def test_convert_polling_mode(self, mock_compute_client, temp_image_file, mandatory_args):
        """Test image-conversion convert in polling mode."""
        # Configure mock
        job = JobResponse(
            job_id="test-job-mno",
            task_type="image_conversion",
            status="completed",
            progress=100,
            params={},
            task_output={"output_path": "/output/image.png"},
            error_message=None,
            priority=5,
            created_at=1234567890000,
            updated_at=1234567890000,
        )
        mock_compute_client.image_conversion.convert = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(
            cli, mandatory_args + ["image-conversion", "convert", str(temp_image_file), "--format", "png"]
        )

        # Verify
        assert result.exit_code == 0
        assert "test-job-mno" in result.output
        mock_compute_client.image_conversion.convert.assert_called_once()

    def test_convert_with_quality(self, mock_compute_client, temp_image_file, mandatory_args):
        """Test image-conversion convert with quality parameter."""
        # Configure mock
        job = JobResponse(
            job_id="test-job-pqr",
            task_type="image_conversion",
            status="completed",
            progress=100,
            params={},
            task_output={"output_path": "/output/image.jpg"},
            error_message=None,
            priority=5,
            created_at=1234567890000,
            updated_at=1234567890000,
        )
        mock_compute_client.image_conversion.convert = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(
            cli,
            mandatory_args + [
                "image-conversion",
                "convert",
                str(temp_image_file),
                "--format",
                "jpg",
                "--quality",
                "90",
            ],
        )

        # Verify
        assert result.exit_code == 0
        # Check that convert was called with quality parameter
        call_kwargs = mock_compute_client.image_conversion.convert.call_args[1]
        assert call_kwargs["quality"] == 90


class TestMediaThumbnail:
    """Tests for media-thumbnail commands."""

    def test_generate_polling_mode(self, mock_compute_client, temp_image_file, mandatory_args):
        """Test media-thumbnail generate in polling mode."""
        # Configure mock
        job = JobResponse(
            job_id="test-job-stu",
            task_type="media_thumbnail",
            status="completed",
            progress=100,
            params={},
            task_output={"thumbnail_path": "/output/thumb.jpg"},
            error_message=None,
            priority=5,
            created_at=1234567890000,
            updated_at=1234567890000,
        )
        mock_compute_client.media_thumbnail.generate = AsyncMock(return_value=job)

        # Run command with required width and height options
        runner = CliRunner()
        result = runner.invoke(
            cli,
            mandatory_args + ["media-thumbnail", "generate", str(temp_image_file), "--width", "256", "--height", "256"],
        )

        # Verify
        assert result.exit_code == 0
        assert "test-job-stu" in result.output
        mock_compute_client.media_thumbnail.generate.assert_called_once()

    def test_generate_with_size(self, mock_compute_client, temp_image_file, mandatory_args):
        """Test media-thumbnail generate with size parameters."""
        # Configure mock
        job = JobResponse(
            job_id="test-job-vwx",
            task_type="media_thumbnail",
            status="completed",
            progress=100,
            params={},
            task_output={"thumbnail_path": "/output/thumb.jpg"},
            error_message=None,
            priority=5,
            created_at=1234567890000,
            updated_at=1234567890000,
        )
        mock_compute_client.media_thumbnail.generate = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(
            cli,
            mandatory_args + [
                "media-thumbnail",
                "generate",
                str(temp_image_file),
                "--width",
                "256",
                "--height",
                "256",
            ],
        )

        # Verify
        assert result.exit_code == 0
        # Check that generate was called with width/height parameters
        call_kwargs = mock_compute_client.media_thumbnail.generate.call_args[1]
        assert call_kwargs["width"] == 256
        assert call_kwargs["height"] == 256


class TestErrorHandling:
    """Tests for error handling."""

    def test_failed_job(self, mock_compute_client, temp_image_file, mandatory_args):
        """Test handling of failed jobs."""
        # Configure mock to return failed job
        failed_job = JobResponse(
            job_id="test-job-fail",
            task_type="clip_embedding",
            status="failed",
            progress=50,
            params={},
            task_output=None,
            error_message="Processing error",
            priority=5,
            created_at=1234567890000,
            updated_at=1234567890000,
        )
        mock_compute_client.clip_embedding.embed_image = AsyncMock(return_value=failed_job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["clip-embedding", "embed", str(temp_image_file)])

        # Should show error but may exit 0 (depends on implementation)
        assert "failed" in result.output.lower() or "error" in result.output.lower()

    def test_timeout_parameter(self, mock_compute_client, temp_image_file, completed_job, mandatory_args):
        """Test timeout parameter is passed correctly."""
        mock_compute_client.clip_embedding.embed_image = AsyncMock(return_value=completed_job)

        # Run command with custom timeout
        runner = CliRunner()
        result = runner.invoke(
            cli, mandatory_args + ["clip-embedding", "embed", "--timeout", "120", str(temp_image_file)]
        )

        # Verify timeout was passed
        assert result.exit_code == 0
        call_kwargs = mock_compute_client.clip_embedding.embed_image.call_args[1]
        assert call_kwargs["timeout"] == 120.0


class TestAdditionalCommands:
    """Additional tests for better coverage."""

    def test_dino_watch_mode(self, mock_compute_client, temp_image_file, mandatory_args):
        """Test dino-embedding with watch mode."""
        job = JobResponse(
            job_id="test-job-watch",
            task_type="dino_embedding",
            status="completed",
            progress=100,
            params={},
            task_output={"embedding": [0.1] * 384},
            error_message=None,
            priority=5,
            created_at=1234567890000,
            updated_at=1234567890000,
        )

        async def mock_embed(**kwargs):
            if "on_complete" in kwargs:
                kwargs["on_complete"](job)
            return job

        mock_compute_client.dino_embedding.embed_image = AsyncMock(side_effect=mock_embed)

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["dino-embedding", "embed", "--watch", str(temp_image_file)])

        assert result.exit_code == 0
        mock_compute_client.dino_embedding.embed_image.assert_called_once()

    def test_exif_watch_mode(self, mock_compute_client, temp_image_file, mandatory_args):
        """Test exif extract with watch mode."""
        job = JobResponse(
            job_id="test-job-exif-watch",
            task_type="exif",
            status="completed",
            progress=100,
            params={},
            task_output={"make": "Canon", "model": "EOS 5D"},
            error_message=None,
            priority=5,
            created_at=1234567890000,
            updated_at=1234567890000,
        )

        async def mock_extract(**kwargs):
            if "on_complete" in kwargs:
                kwargs["on_complete"](job)
            return job

        mock_compute_client.exif.extract = AsyncMock(side_effect=mock_extract)

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["exif", "extract", "--watch", str(temp_image_file)])

        assert result.exit_code == 0
        mock_compute_client.exif.extract.assert_called_once()

    def test_hash_watch_mode(self, mock_compute_client, temp_image_file, mandatory_args):
        """Test hash compute with watch mode."""
        job = JobResponse(
            job_id="test-job-hash-watch",
            task_type="hash",
            status="completed",
            progress=100,
            params={},
            task_output={"phash": "abc123", "dhash": "def456"},
            error_message=None,
            priority=5,
            created_at=1234567890000,
            updated_at=1234567890000,
        )

        async def mock_compute(**kwargs):
            if "on_complete" in kwargs:
                kwargs["on_complete"](job)
            return job

        mock_compute_client.hash.compute = AsyncMock(side_effect=mock_compute)

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["hash", "compute", "--watch", str(temp_image_file)])

        assert result.exit_code == 0
        mock_compute_client.hash.compute.assert_called_once()

    def test_image_conversion_watch_mode(self, mock_compute_client, temp_image_file, mandatory_args):
        """Test image-conversion convert with watch mode."""
        job = JobResponse(
            job_id="test-job-convert-watch",
            task_type="image_conversion",
            status="completed",
            progress=100,
            params={},
            task_output={"output_path": "/output/image.png"},
            error_message=None,
            priority=5,
            created_at=1234567890000,
            updated_at=1234567890000,
        )

        async def mock_convert(**kwargs):
            if "on_complete" in kwargs:
                kwargs["on_complete"](job)
            return job

        mock_compute_client.image_conversion.convert = AsyncMock(side_effect=mock_convert)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            mandatory_args + ["image-conversion", "convert", "--watch", str(temp_image_file), "--format", "png"],
        )

        assert result.exit_code == 0
        mock_compute_client.image_conversion.convert.assert_called_once()

    def test_media_thumbnail_watch_mode(self, mock_compute_client, temp_image_file, mandatory_args):
        """Test media-thumbnail generate with watch mode."""
        job = JobResponse(
            job_id="test-job-thumb-watch",
            task_type="media_thumbnail",
            status="completed",
            progress=100,
            params={},
            task_output={"thumbnail_path": "/output/thumb.jpg"},
            error_message=None,
            priority=5,
            created_at=1234567890000,
            updated_at=1234567890000,
        )

        async def mock_generate(**kwargs):
            if "on_complete" in kwargs:
                kwargs["on_complete"](job)
            return job

        mock_compute_client.media_thumbnail.generate = AsyncMock(side_effect=mock_generate)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            mandatory_args + [
                "media-thumbnail",
                "generate",
                "--watch",
                str(temp_image_file),
                "--width",
                "256",
                "--height",
                "256",
            ],
        )

        assert result.exit_code == 0
        mock_compute_client.media_thumbnail.generate.assert_called_once()


class TestStoreCommands:
    """Tests for store commands."""

    def test_store_list_success(self, mock_store_manager, sample_entity_list, mandatory_args):
        """Test store list command."""
        # Configure mock to return success result
        mock_store_manager.list_entities.return_value = StoreOperationResult[EntityListResponse](
            success="Entities retrieved successfully",
            data=sample_entity_list,
        )

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "list"])

        # Verify
        assert result.exit_code == 0
        assert "Entity 1" in result.output
        assert "Entity 2" in result.output
        mock_store_manager.list_entities.assert_called_once()

    def test_store_list_with_pagination(self, mock_store_manager, sample_entity_list, mandatory_args):
        """Test store list with pagination options."""
        mock_store_manager.list_entities.return_value = StoreOperationResult[EntityListResponse](
            success="Success",
            data=sample_entity_list,
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "list", "--page", "2", "--page-size", "10"])

        assert result.exit_code == 0
        # Verify pagination parameters were passed
        call_kwargs = mock_store_manager.list_entities.call_args[1]
        assert call_kwargs["page"] == 2
        assert call_kwargs["page_size"] == 10

    def test_store_list_with_search(self, mock_store_manager, sample_entity_list, mandatory_args):
        """Test store list with search query."""
        mock_store_manager.list_entities.return_value = StoreOperationResult[EntityListResponse](
            success="Success",
            data=sample_entity_list,
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "list", "--search", "test query"])

        assert result.exit_code == 0
        call_kwargs = mock_store_manager.list_entities.call_args[1]
        assert call_kwargs["search_query"] == "test query"

    def test_store_list_error(self, mock_store_manager, mandatory_args):
        """Test store list with error."""
        mock_store_manager.list_entities.return_value = StoreOperationResult[EntityListResponse](
            error="Unauthorized: Invalid token",
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "list"])

        assert result.exit_code != 0
        assert "Unauthorized" in result.output

    def test_store_get_success(self, mock_store_manager, sample_entity, mandatory_args):
        """Test store get command."""
        mock_store_manager.read_entity.return_value = StoreOperationResult[Entity](
            success="Entity retrieved successfully",
            data=sample_entity,
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "get", "1"])

        assert result.exit_code == 0
        assert "Test Entity" in result.output
        assert "Test description" in result.output
        mock_store_manager.read_entity.assert_called_once_with(entity_id=1, version=None)

    def test_store_get_with_version(self, mock_store_manager, sample_entity, mandatory_args):
        """Test store get with specific version."""
        mock_store_manager.read_entity.return_value = StoreOperationResult[Entity](
            success="Success",
            data=sample_entity,
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "get", "1", "--version", "2"])

        assert result.exit_code == 0
        call_kwargs = mock_store_manager.read_entity.call_args[1]
        assert call_kwargs["version"] == 2

    def test_store_create_collection(self, mock_store_manager, sample_collection, mandatory_args):
        """Test creating a collection."""
        mock_store_manager.create_entity.return_value = StoreOperationResult[Entity](
            success="Entity created successfully",
            data=sample_collection,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            mandatory_args + ["store", "create", "--label", "Test Collection", "--collection"],
        )

        assert result.exit_code == 0
        # Parse JSON output and verify entity data
        output_data = json.loads(result.output)
        assert output_data["id"] == 2
        assert output_data["is_collection"] is True
        assert output_data["label"] == "Test Collection"
        call_kwargs = mock_store_manager.create_entity.call_args[1]
        assert call_kwargs["label"] == "Test Collection"
        assert call_kwargs["is_collection"] is True

    def test_store_create_with_file(self, mock_store_manager, sample_entity, temp_image_file, mandatory_args):
        """Test creating entity with file upload."""
        mock_store_manager.create_entity.return_value = StoreOperationResult[Entity](
            success="Entity created successfully",
            data=sample_entity,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            mandatory_args + [
                "store",
                "create",
                "--label",
                "Photo",
                "--description",
                "Test photo",
                "--file",
                str(temp_image_file),
            ],
        )

        assert result.exit_code == 0
        # Parse JSON output and verify entity data
        output_data = json.loads(result.output)
        assert output_data["id"] == 1
        assert output_data["label"] == "Test Entity"
        call_kwargs = mock_store_manager.create_entity.call_args[1]
        assert call_kwargs["label"] == "Photo"
        assert call_kwargs["description"] == "Test photo"
        assert call_kwargs["image_path"] is not None

    def test_store_update_success(self, mock_store_manager, sample_entity, mandatory_args):
        """Test store update command."""
        mock_store_manager.update_entity.return_value = StoreOperationResult[Entity](
            success="Entity updated successfully",
            data=sample_entity,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            mandatory_args + ["store", "update", "1", "--label", "Updated Label"],
        )

        assert result.exit_code == 0
        assert "Updated entity" in result.output
        call_kwargs = mock_store_manager.update_entity.call_args[1]
        assert call_kwargs["entity_id"] == 1
        assert call_kwargs["label"] == "Updated Label"

    def test_store_patch_label(self, mock_store_manager, sample_entity, mandatory_args):
        """Test store patch command for label."""
        mock_store_manager.patch_entity.return_value = StoreOperationResult[Entity](
            success="Entity patched successfully",
            data=sample_entity,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            mandatory_args + ["store", "patch", "1", "--label", "Patched Label"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_store_manager.patch_entity.call_args[1]
        assert call_kwargs["entity_id"] == 1
        assert call_kwargs["label"] == "Patched Label"

    def test_store_patch_soft_delete(self, mock_store_manager, sample_entity, mandatory_args):
        """Test store patch for soft delete."""
        deleted_entity = Entity(id=1, label="Test", is_deleted=True)
        mock_store_manager.patch_entity.return_value = StoreOperationResult[Entity](
            success="Entity patched successfully",
            data=deleted_entity,
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "patch", "1", "--delete"])

        assert result.exit_code == 0
        assert "Deleted entity" in result.output
        call_kwargs = mock_store_manager.patch_entity.call_args[1]
        assert call_kwargs["is_deleted"] is True

    def test_store_patch_restore(self, mock_store_manager, sample_entity, mandatory_args):
        """Test store patch for restore."""
        mock_store_manager.patch_entity.return_value = StoreOperationResult[Entity](
            success="Entity patched successfully",
            data=sample_entity,
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "patch", "1", "--restore"])

        assert result.exit_code == 0
        assert "Restored entity" in result.output
        call_kwargs = mock_store_manager.patch_entity.call_args[1]
        assert call_kwargs["is_deleted"] is False

    def test_store_delete_success(self, mock_store_manager, mandatory_args):
        """Test store delete command."""
        mock_store_manager.delete_entity.return_value = StoreOperationResult[None](
            success="Entity deleted successfully",
            data=None,
        )

        runner = CliRunner()
        # Use --yes flag to bypass confirmation
        result = runner.invoke(cli, mandatory_args + ["store", "delete", "1", "--yes"])

        assert result.exit_code == 0
        assert "Deleted entity" in result.output
        mock_store_manager.delete_entity.assert_called_once_with(entity_id=1)

    def test_store_versions_success(self, mock_store_manager, sample_versions, mandatory_args):
        """Test store versions command."""
        mock_store_manager.get_versions.return_value = StoreOperationResult[list](
            success="Version history retrieved successfully",
            data=sample_versions,
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "versions", "1"])

        assert result.exit_code == 0
        assert "Version 1" in result.output
        assert "Version 2" in result.output
        mock_store_manager.get_versions.assert_called_once_with(entity_id=1)

    def test_store_admin_config(self, mock_store_manager, sample_store_pref, mandatory_args):
        """Test store admin config command."""
        mock_store_manager.get_pref.return_value = StoreOperationResult(
            success="Configuration retrieved successfully",
            data=sample_store_pref,
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "admin", "config"])

        assert result.exit_code == 0
        # Parse JSON output and verify config data
        output_data = json.loads(result.output)
        assert output_data["guest_mode"] is False
        assert "updated_at" in output_data
        mock_store_manager.get_pref.assert_called_once()

    def test_store_admin_set_guest_mode(self, mock_store_manager, sample_store_pref, mandatory_args):
        """Test store admin set-guest-mode command."""
        mock_store_manager.update_guest_mode.return_value = StoreOperationResult(
            success="Configuration updated successfully",
            data=sample_store_pref,
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "admin", "set-guest-mode", "false"])

        # Verify config was updated
        assert result.exit_code == 0
        assert "disabled" in result.output
        mock_store_manager.update_guest_mode.assert_called_once_with(guest_mode=False)


    def test_store_face_delete_success(self, mock_store_manager, mandatory_args):
        """Test store face delete command."""
        mock_store_manager.delete_face.return_value = StoreOperationResult(
            success="Face deleted successfully",
            data=None,
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "face", "delete", "1", "--yes"])

        assert result.exit_code == 0
        assert "success" in result.output
        mock_store_manager.delete_face.assert_called_once_with(1)

    def test_store_intelligence_success(self, mock_store_manager, sample_entity_intelligence: EntityIntelligenceData, mandatory_args):
        """Test store intelligence command."""
        mock_store_manager.get_entity_intelligence.return_value = StoreOperationResult(
            success="Intelligence data retrieved successfully",
            data=sample_entity_intelligence,
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "intelligence", "1"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["overall_status"] == "completed"
        mock_store_manager.get_entity_intelligence.assert_called_once_with(1)

    def test_store_admin_audit_report(self, mock_store_manager, sample_audit_report, mandatory_args):
        """Test store admin audit-report command."""
        mock_store_manager.get_audit_report.return_value = StoreOperationResult(
            success="Audit report retrieved successfully",
            data=sample_audit_report,
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "admin", "audit-report"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "orphaned_files" in data
        mock_store_manager.get_audit_report.assert_called_once()

    def test_store_admin_clear_orphans(self, mock_store_manager, sample_cleanup_report, mandatory_args):
        """Test store admin clear-orphans command."""
        mock_store_manager.clear_orphans.return_value = StoreOperationResult(
            success="Orphans cleared successfully",
            data=sample_cleanup_report,
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "admin", "clear-orphans", "--yes"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "files_deleted" in data
        mock_store_manager.clear_orphans.assert_called_once()


class TestAuthErrors:
    """Tests for authentication error scenarios."""

    def test_unauthorized_error(self, mock_store_manager, mandatory_args):
        """Test handling of 401 Unauthorized errors."""
        mock_store_manager.list_entities.return_value = StoreOperationResult(
            error="Unauthorized: Invalid token",
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "list"])

        assert result.exit_code != 0
        assert "Unauthorized" in result.output

    def test_forbidden_error(self, mock_store_manager, mandatory_args):
        """Test handling of 403 Forbidden errors."""
        mock_store_manager.get_pref.return_value = StoreOperationResult(
            error="Forbidden: Admin access required",
        )

        runner = CliRunner()
        result = runner.invoke(cli, mandatory_args + ["store", "admin", "config"])

        assert result.exit_code != 0
        assert "Forbidden" in result.output
