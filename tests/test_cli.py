"""Unit tests for CLI commands."""

from unittest.mock import AsyncMock

from click.testing import CliRunner

from cl_client.models import JobResponse
from cl_client.store_models import Entity, EntityListResponse, StoreConfig, StoreOperationResult
from cl_client_cli.main import cli


class TestClipEmbedding:
    """Tests for clip-embedding commands."""

    def test_embed_polling_mode(self, mock_compute_client, temp_image_file, completed_job):
        """Test clip-embedding embed in polling mode."""
        # Configure mock
        mock_compute_client.clip_embedding.embed_image = AsyncMock(return_value=completed_job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["clip-embedding", "embed", str(temp_image_file)])

        # Verify
        assert result.exit_code == 0
        assert "test-job-123" in result.output
        assert "completed" in result.output.lower()
        mock_compute_client.clip_embedding.embed_image.assert_called_once()

    def test_embed_watch_mode(self, mock_compute_client, temp_image_file, completed_job):
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
        result = runner.invoke(cli, ["clip-embedding", "embed", "--watch", str(temp_image_file)])

        # Verify
        assert result.exit_code == 0
        mock_compute_client.clip_embedding.embed_image.assert_called_once()

    def test_embed_missing_file(self, mock_compute_client):
        """Test clip-embedding embed with missing file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["clip-embedding", "embed", "/nonexistent/file.jpg"])

        # Should fail validation before calling API
        assert result.exit_code != 0


class TestDinoEmbedding:
    """Tests for dino-embedding commands."""

    def test_embed_polling_mode(self, mock_compute_client, temp_image_file, completed_job):
        """Test dino-embedding embed in polling mode."""
        # Configure mock
        job = JobResponse(
            job_id="test-job-456",
            task_type="dino_embedding",
            status="completed",
            progress=100,
            params={},
            task_output={"embedding": [0.1] * 384},
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )
        mock_compute_client.dino_embedding.embed_image = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["dino-embedding", "embed", str(temp_image_file)])

        # Verify
        assert result.exit_code == 0
        assert "test-job-456" in result.output
        mock_compute_client.dino_embedding.embed_image.assert_called_once()


class TestExif:
    """Tests for exif commands."""

    def test_extract_polling_mode(self, mock_compute_client, temp_image_file):
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
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )
        mock_compute_client.exif.extract = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["exif", "extract", str(temp_image_file)])

        # Verify
        assert result.exit_code == 0
        assert "Canon" in result.output
        assert "EOS 5D Mark IV" in result.output
        mock_compute_client.exif.extract.assert_called_once()


class TestFaceDetection:
    """Tests for face-detection commands."""

    def test_detect_polling_mode(self, mock_compute_client, temp_image_file):
        """Test face-detection detect in polling mode."""
        # Configure mock
        job = JobResponse(
            job_id="test-job-abc",
            task_type="face_detection",
            status="completed",
            progress=100,
            params={},
            task_output={
                "faces": [
                    {"x": 100, "y": 150, "width": 200, "height": 250, "confidence": 0.99},
                    {"x": 400, "y": 200, "width": 180, "height": 220, "confidence": 0.95},
                ]
            },
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )
        mock_compute_client.face_detection.detect = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["face-detection", "detect", str(temp_image_file)])

        # Verify
        assert result.exit_code == 0
        assert "test-job-abc" in result.output
        assert "completed" in result.output.lower()
        mock_compute_client.face_detection.detect.assert_called_once()


class TestFaceEmbedding:
    """Tests for face-embedding commands."""

    def test_embed_polling_mode(self, mock_compute_client, temp_image_file):
        """Test face-embedding embed in polling mode."""
        # Configure mock
        job = JobResponse(
            job_id="test-job-def",
            task_type="face_embedding",
            status="completed",
            progress=100,
            params={},
            task_output={"embeddings": [[0.1] * 128]},
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )
        mock_compute_client.face_embedding.embed_faces = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["face-embedding", "embed", str(temp_image_file)])

        # Verify
        assert result.exit_code == 0
        assert "test-job-def" in result.output
        mock_compute_client.face_embedding.embed_faces.assert_called_once()


class TestHash:
    """Tests for hash commands."""

    def test_compute_polling_mode(self, mock_compute_client, temp_image_file):
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
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )
        mock_compute_client.hash.compute = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["hash", "compute", str(temp_image_file)])

        # Verify
        assert result.exit_code == 0
        assert "abcdef1234567890" in result.output
        assert "fedcba0987654321" in result.output
        mock_compute_client.hash.compute.assert_called_once()


class TestHlsStreaming:
    """Tests for hls-streaming commands."""

    def test_generate_manifest_polling_mode(self, mock_compute_client, temp_video_file):
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
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )
        mock_compute_client.hls_streaming.generate_manifest = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["hls-streaming", "generate-manifest", str(temp_video_file)])

        # Verify
        assert result.exit_code == 0
        assert "manifest.m3u8" in result.output
        mock_compute_client.hls_streaming.generate_manifest.assert_called_once()


class TestImageConversion:
    """Tests for image-conversion commands."""

    def test_convert_polling_mode(self, mock_compute_client, temp_image_file):
        """Test image-conversion convert in polling mode."""
        # Configure mock
        job = JobResponse(
            job_id="test-job-mno",
            task_type="image_conversion",
            status="completed",
            progress=100,
            params={},
            task_output={"output_path": "/output/image.png"},
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )
        mock_compute_client.image_conversion.convert = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(
            cli, ["image-conversion", "convert", str(temp_image_file), "--format", "png"]
        )

        # Verify
        assert result.exit_code == 0
        assert "test-job-mno" in result.output
        mock_compute_client.image_conversion.convert.assert_called_once()

    def test_convert_with_quality(self, mock_compute_client, temp_image_file):
        """Test image-conversion convert with quality parameter."""
        # Configure mock
        job = JobResponse(
            job_id="test-job-pqr",
            task_type="image_conversion",
            status="completed",
            progress=100,
            params={},
            task_output={"output_path": "/output/image.jpg"},
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )
        mock_compute_client.image_conversion.convert = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
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

    def test_generate_polling_mode(self, mock_compute_client, temp_image_file):
        """Test media-thumbnail generate in polling mode."""
        # Configure mock
        job = JobResponse(
            job_id="test-job-stu",
            task_type="media_thumbnail",
            status="completed",
            progress=100,
            params={},
            task_output={"thumbnail_path": "/output/thumb.jpg"},
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )
        mock_compute_client.media_thumbnail.generate = AsyncMock(return_value=job)

        # Run command with required width and height options
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["media-thumbnail", "generate", str(temp_image_file), "--width", "256", "--height", "256"],
        )

        # Verify
        assert result.exit_code == 0
        assert "test-job-stu" in result.output
        mock_compute_client.media_thumbnail.generate.assert_called_once()

    def test_generate_with_size(self, mock_compute_client, temp_image_file):
        """Test media-thumbnail generate with size parameters."""
        # Configure mock
        job = JobResponse(
            job_id="test-job-vwx",
            task_type="media_thumbnail",
            status="completed",
            progress=100,
            params={},
            task_output={"thumbnail_path": "/output/thumb.jpg"},
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )
        mock_compute_client.media_thumbnail.generate = AsyncMock(return_value=job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
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

    def test_failed_job(self, mock_compute_client, temp_image_file):
        """Test handling of failed jobs."""
        # Configure mock to return failed job
        failed_job = JobResponse(
            job_id="test-job-fail",
            task_type="clip_embedding",
            status="failed",
            progress=50,
            params={},
            error_message="Processing error",
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )
        mock_compute_client.clip_embedding.embed_image = AsyncMock(return_value=failed_job)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["clip-embedding", "embed", str(temp_image_file)])

        # Should show error but may exit 0 (depends on implementation)
        assert "failed" in result.output.lower() or "error" in result.output.lower()

    def test_timeout_parameter(self, mock_compute_client, temp_image_file, completed_job):
        """Test timeout parameter is passed correctly."""
        mock_compute_client.clip_embedding.embed_image = AsyncMock(return_value=completed_job)

        # Run command with custom timeout
        runner = CliRunner()
        result = runner.invoke(
            cli, ["clip-embedding", "embed", "--timeout", "120", str(temp_image_file)]
        )

        # Verify timeout was passed
        assert result.exit_code == 0
        call_kwargs = mock_compute_client.clip_embedding.embed_image.call_args[1]
        assert call_kwargs["timeout"] == 120.0


class TestAdditionalCommands:
    """Additional tests for better coverage."""

    def test_dino_watch_mode(self, mock_compute_client, temp_image_file):
        """Test dino-embedding with watch mode."""
        job = JobResponse(
            job_id="test-job-watch",
            task_type="dino_embedding",
            status="completed",
            progress=100,
            params={},
            task_output={"embedding": [0.1] * 384},
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )

        async def mock_embed(**kwargs):
            if "on_complete" in kwargs:
                kwargs["on_complete"](job)
            return job

        mock_compute_client.dino_embedding.embed_image = AsyncMock(side_effect=mock_embed)

        runner = CliRunner()
        result = runner.invoke(cli, ["dino-embedding", "embed", "--watch", str(temp_image_file)])

        assert result.exit_code == 0
        mock_compute_client.dino_embedding.embed_image.assert_called_once()

    def test_exif_watch_mode(self, mock_compute_client, temp_image_file):
        """Test exif extract with watch mode."""
        job = JobResponse(
            job_id="test-job-exif-watch",
            task_type="exif",
            status="completed",
            progress=100,
            params={},
            task_output={"make": "Canon", "model": "EOS 5D"},
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )

        async def mock_extract(**kwargs):
            if "on_complete" in kwargs:
                kwargs["on_complete"](job)
            return job

        mock_compute_client.exif.extract = AsyncMock(side_effect=mock_extract)

        runner = CliRunner()
        result = runner.invoke(cli, ["exif", "extract", "--watch", str(temp_image_file)])

        assert result.exit_code == 0
        mock_compute_client.exif.extract.assert_called_once()

    def test_hash_watch_mode(self, mock_compute_client, temp_image_file):
        """Test hash compute with watch mode."""
        job = JobResponse(
            job_id="test-job-hash-watch",
            task_type="hash",
            status="completed",
            progress=100,
            params={},
            task_output={"phash": "abc123", "dhash": "def456"},
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )

        async def mock_compute(**kwargs):
            if "on_complete" in kwargs:
                kwargs["on_complete"](job)
            return job

        mock_compute_client.hash.compute = AsyncMock(side_effect=mock_compute)

        runner = CliRunner()
        result = runner.invoke(cli, ["hash", "compute", "--watch", str(temp_image_file)])

        assert result.exit_code == 0
        mock_compute_client.hash.compute.assert_called_once()

    def test_face_detection_watch_mode(self, mock_compute_client, temp_image_file):
        """Test face-detection detect with watch mode."""
        job = JobResponse(
            job_id="test-job-face-watch",
            task_type="face_detection",
            status="completed",
            progress=100,
            params={},
            task_output={"faces": []},
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )

        async def mock_detect(**kwargs):
            if "on_complete" in kwargs:
                kwargs["on_complete"](job)
            return job

        mock_compute_client.face_detection.detect = AsyncMock(side_effect=mock_detect)

        runner = CliRunner()
        result = runner.invoke(cli, ["face-detection", "detect", "--watch", str(temp_image_file)])

        assert result.exit_code == 0
        mock_compute_client.face_detection.detect.assert_called_once()

    def test_image_conversion_watch_mode(self, mock_compute_client, temp_image_file):
        """Test image-conversion convert with watch mode."""
        job = JobResponse(
            job_id="test-job-convert-watch",
            task_type="image_conversion",
            status="completed",
            progress=100,
            params={},
            task_output={"output_path": "/output/image.png"},
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )

        async def mock_convert(**kwargs):
            if "on_complete" in kwargs:
                kwargs["on_complete"](job)
            return job

        mock_compute_client.image_conversion.convert = AsyncMock(side_effect=mock_convert)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["image-conversion", "convert", "--watch", str(temp_image_file), "--format", "png"],
        )

        assert result.exit_code == 0
        mock_compute_client.image_conversion.convert.assert_called_once()

    def test_media_thumbnail_watch_mode(self, mock_compute_client, temp_image_file):
        """Test media-thumbnail generate with watch mode."""
        job = JobResponse(
            job_id="test-job-thumb-watch",
            task_type="media_thumbnail",
            status="completed",
            progress=100,
            params={},
            task_output={"thumbnail_path": "/output/thumb.jpg"},
            priority=5,
            created_at=1234567890000,
            completed_at=1234567891000,
        )

        async def mock_generate(**kwargs):
            if "on_complete" in kwargs:
                kwargs["on_complete"](job)
            return job

        mock_compute_client.media_thumbnail.generate = AsyncMock(side_effect=mock_generate)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
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

    def test_store_list_success(self, mock_store_manager, sample_entity_list):
        """Test store list command."""
        # Configure mock to return success result
        mock_store_manager.list_entities.return_value = StoreOperationResult[EntityListResponse](
            success="Entities retrieved successfully",
            data=sample_entity_list,
        )

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["store", "list"])

        # Verify
        assert result.exit_code == 0
        assert "Entity 1" in result.output
        assert "Entity 2" in result.output
        mock_store_manager.list_entities.assert_called_once()

    def test_store_list_with_pagination(self, mock_store_manager, sample_entity_list):
        """Test store list with pagination options."""
        mock_store_manager.list_entities.return_value = StoreOperationResult[EntityListResponse](
            success="Success",
            data=sample_entity_list,
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["store", "list", "--page", "2", "--page-size", "10"])

        assert result.exit_code == 0
        # Verify pagination parameters were passed
        call_kwargs = mock_store_manager.list_entities.call_args[1]
        assert call_kwargs["page"] == 2
        assert call_kwargs["page_size"] == 10

    def test_store_list_with_search(self, mock_store_manager, sample_entity_list):
        """Test store list with search query."""
        mock_store_manager.list_entities.return_value = StoreOperationResult[EntityListResponse](
            success="Success",
            data=sample_entity_list,
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["store", "list", "--search", "test query"])

        assert result.exit_code == 0
        call_kwargs = mock_store_manager.list_entities.call_args[1]
        assert call_kwargs["search_query"] == "test query"

    def test_store_list_error(self, mock_store_manager):
        """Test store list with error."""
        mock_store_manager.list_entities.return_value = StoreOperationResult[EntityListResponse](
            error="Unauthorized: Invalid token",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["store", "list"])

        assert result.exit_code != 0
        assert "Unauthorized" in result.output

    def test_store_get_success(self, mock_store_manager, sample_entity):
        """Test store get command."""
        mock_store_manager.read_entity.return_value = StoreOperationResult[Entity](
            success="Entity retrieved successfully",
            data=sample_entity,
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["store", "get", "1"])

        assert result.exit_code == 0
        assert "Test Entity" in result.output
        assert "Test description" in result.output
        mock_store_manager.read_entity.assert_called_once_with(entity_id=1, version=None)

    def test_store_get_with_version(self, mock_store_manager, sample_entity):
        """Test store get with specific version."""
        mock_store_manager.read_entity.return_value = StoreOperationResult[Entity](
            success="Success",
            data=sample_entity,
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["store", "get", "1", "--version", "2"])

        assert result.exit_code == 0
        call_kwargs = mock_store_manager.read_entity.call_args[1]
        assert call_kwargs["version"] == 2

    def test_store_create_collection(self, mock_store_manager, sample_collection):
        """Test creating a collection."""
        mock_store_manager.create_entity.return_value = StoreOperationResult[Entity](
            success="Entity created successfully",
            data=sample_collection,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["store", "create", "--label", "Test Collection", "--collection"],
        )

        assert result.exit_code == 0
        assert "Created entity" in result.output
        call_kwargs = mock_store_manager.create_entity.call_args[1]
        assert call_kwargs["label"] == "Test Collection"
        assert call_kwargs["is_collection"] is True

    def test_store_create_with_file(self, mock_store_manager, sample_entity, temp_image_file):
        """Test creating entity with file upload."""
        mock_store_manager.create_entity.return_value = StoreOperationResult[Entity](
            success="Entity created successfully",
            data=sample_entity,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
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
        assert "Created entity" in result.output
        call_kwargs = mock_store_manager.create_entity.call_args[1]
        assert call_kwargs["label"] == "Photo"
        assert call_kwargs["description"] == "Test photo"
        assert call_kwargs["image_path"] is not None

    def test_store_update_success(self, mock_store_manager, sample_entity):
        """Test store update command."""
        mock_store_manager.update_entity.return_value = StoreOperationResult[Entity](
            success="Entity updated successfully",
            data=sample_entity,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["store", "update", "1", "--label", "Updated Label"],
        )

        assert result.exit_code == 0
        assert "Updated entity" in result.output
        call_kwargs = mock_store_manager.update_entity.call_args[1]
        assert call_kwargs["entity_id"] == 1
        assert call_kwargs["label"] == "Updated Label"

    def test_store_patch_label(self, mock_store_manager, sample_entity):
        """Test store patch command for label."""
        mock_store_manager.patch_entity.return_value = StoreOperationResult[Entity](
            success="Entity patched successfully",
            data=sample_entity,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["store", "patch", "1", "--label", "Patched Label"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_store_manager.patch_entity.call_args[1]
        assert call_kwargs["entity_id"] == 1
        assert call_kwargs["label"] == "Patched Label"

    def test_store_patch_soft_delete(self, mock_store_manager, sample_entity):
        """Test store patch for soft delete."""
        deleted_entity = Entity(id=1, label="Test", is_deleted=True)
        mock_store_manager.patch_entity.return_value = StoreOperationResult[Entity](
            success="Entity patched successfully",
            data=deleted_entity,
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["store", "patch", "1", "--delete"])

        assert result.exit_code == 0
        assert "Deleted entity" in result.output
        call_kwargs = mock_store_manager.patch_entity.call_args[1]
        assert call_kwargs["is_deleted"] is True

    def test_store_patch_restore(self, mock_store_manager, sample_entity):
        """Test store patch for restore."""
        mock_store_manager.patch_entity.return_value = StoreOperationResult[Entity](
            success="Entity patched successfully",
            data=sample_entity,
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["store", "patch", "1", "--restore"])

        assert result.exit_code == 0
        assert "Restored entity" in result.output
        call_kwargs = mock_store_manager.patch_entity.call_args[1]
        assert call_kwargs["is_deleted"] is False

    def test_store_delete_success(self, mock_store_manager):
        """Test store delete command."""
        mock_store_manager.delete_entity.return_value = StoreOperationResult[None](
            success="Entity deleted successfully",
            data=None,
        )

        runner = CliRunner()
        # Use --yes flag to bypass confirmation
        result = runner.invoke(cli, ["store", "delete", "1", "--yes"])

        assert result.exit_code == 0
        assert "Deleted entity" in result.output
        mock_store_manager.delete_entity.assert_called_once_with(entity_id=1)

    def test_store_versions_success(self, mock_store_manager, sample_versions):
        """Test store versions command."""
        mock_store_manager.get_versions.return_value = StoreOperationResult[list](
            success="Version history retrieved successfully",
            data=sample_versions,
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["store", "versions", "1"])

        assert result.exit_code == 0
        assert "Version 1" in result.output
        assert "Version 2" in result.output
        mock_store_manager.get_versions.assert_called_once_with(entity_id=1)

    def test_store_admin_config(self, mock_store_manager, sample_store_config):
        """Test store admin config command."""
        mock_store_manager.get_config.return_value = StoreOperationResult(
            success="Configuration retrieved successfully",
            data=sample_store_config,
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["store", "admin", "config"])

        assert result.exit_code == 0
        assert "Store Configuration" in result.output
        assert "Disabled" in result.output  # guest_mode is displayed as "Disabled"
        mock_store_manager.get_config.assert_called_once()

    def test_store_admin_set_guest_mode(self, mock_store_manager, sample_store_config):
        """Test store admin set-guest-mode command."""
        updated_config = StoreConfig(
            guest_mode=False,
            updated_at=1704153600000,
            updated_by="admin",
        )
        mock_store_manager.update_guest_mode.return_value = StoreOperationResult(
            success="Guest mode configuration updated successfully",
            data=updated_config,
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["store", "admin", "set-guest-mode", "false"])

        assert result.exit_code == 0
        assert "disabled" in result.output
        mock_store_manager.update_guest_mode.assert_called_once_with(guest_mode=False)

    def test_store_list_with_output_file(self, mock_store_manager, sample_entity_list, tmp_path):
        """Test store list with JSON output file."""
        output_file = tmp_path / "entities.json"
        mock_store_manager.list_entities.return_value = StoreOperationResult[EntityListResponse](
            success="Success",
            data=sample_entity_list,
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["store", "list", "--output", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        assert "Saved to" in result.output

    def test_store_get_with_output_file(self, mock_store_manager, sample_entity, tmp_path):
        """Test store get with JSON output file."""
        output_file = tmp_path / "entity.json"
        mock_store_manager.read_entity.return_value = StoreOperationResult[Entity](
            success="Success",
            data=sample_entity,
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["store", "get", "1", "--output", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        assert "Saved to" in result.output


class TestNewDatabaseCommands:
    """Test database feature commands (jobs, faces, persons, images)."""

    def test_store_jobs(self, mock_store_manager, sample_entity_job):
        """Test store jobs command."""
        mock_store_manager.store_client.get_entity_jobs.return_value = [sample_entity_job]

        runner = CliRunner()
        result = runner.invoke(cli, ["store", "jobs", "123"])

        assert result.exit_code == 0
        assert "Entity Jobs for ID: 123" in result.output
        assert "Total jobs: 1" in result.output
        mock_store_manager.store_client.get_entity_jobs.assert_called_once_with(entity_id=123)

    def test_faces_list(self, mock_store_manager, sample_face):
        """Test faces list command."""
        mock_store_manager.store_client.get_entity_faces.return_value = [sample_face]

        runner = CliRunner()
        result = runner.invoke(cli, ["faces", "list", "123"])

        assert result.exit_code == 0
        assert "Faces in Entity ID: 123" in result.output
        assert "Total faces: 1" in result.output
        mock_store_manager.store_client.get_entity_faces.assert_called_once_with(entity_id=123)

    def test_faces_similar(self, mock_store_manager, sample_similar_faces_response):
        """Test faces similar command."""
        mock_store_manager.store_client.find_similar_faces.return_value = sample_similar_faces_response

        runner = CliRunner()
        result = runner.invoke(cli, ["faces", "similar", "456", "--limit", "10", "--threshold", "0.7"])

        assert result.exit_code == 0
        assert "Similar Faces for Face ID: 456" in result.output
        mock_store_manager.store_client.find_similar_faces.assert_called_once_with(
            face_id=456,
            limit=10,
            threshold=0.7,
        )

    def test_faces_download_embedding(self, mock_store_manager, tmp_path):
        """Test faces download-embedding command."""
        output_file = tmp_path / "face.npy"
        mock_store_manager.store_client.download_face_embedding.return_value = None

        runner = CliRunner()
        result = runner.invoke(cli, ["faces", "download-embedding", "456", "--output", str(output_file)])

        assert result.exit_code == 0
        assert "Face embedding downloaded" in result.output
        mock_store_manager.store_client.download_face_embedding.assert_called_once()

    def test_faces_matches(self, mock_store_manager, sample_face_match):
        """Test faces matches command."""
        mock_store_manager.store_client.get_face_matches.return_value = [sample_face_match]

        runner = CliRunner()
        result = runner.invoke(cli, ["faces", "matches", "456"])

        assert result.exit_code == 0
        assert "Match History for Face ID: 456" in result.output
        assert "Total matches: 1" in result.output
        mock_store_manager.store_client.get_face_matches.assert_called_once_with(face_id=456)

    def test_persons_list(self, mock_store_manager, sample_known_person):
        """Test persons list command."""
        mock_store_manager.store_client.get_all_known_persons.return_value = [sample_known_person]

        runner = CliRunner()
        result = runner.invoke(cli, ["persons", "list"])

        assert result.exit_code == 0
        assert "Known Persons" in result.output
        assert "Total persons: 1" in result.output
        mock_store_manager.store_client.get_all_known_persons.assert_called_once()

    def test_persons_get(self, mock_store_manager, sample_known_person):
        """Test persons get command."""
        mock_store_manager.store_client.get_known_person.return_value = sample_known_person

        runner = CliRunner()
        result = runner.invoke(cli, ["persons", "get", "789"])

        assert result.exit_code == 0
        assert "Person ID: 789" in result.output
        mock_store_manager.store_client.get_known_person.assert_called_once_with(person_id=789)

    def test_persons_update(self, mock_store_manager, sample_known_person):
        """Test persons update command."""
        mock_store_manager.store_client.update_known_person_name.return_value = sample_known_person

        runner = CliRunner()
        result = runner.invoke(cli, ["persons", "update", "789", "--name", "Jane Doe"])

        assert result.exit_code == 0
        assert "Updated person 789" in result.output
        mock_store_manager.store_client.update_known_person_name.assert_called_once_with(
            person_id=789,
            name="Jane Doe",
        )

    def test_persons_faces(self, mock_store_manager, sample_face):
        """Test persons faces command."""
        mock_store_manager.store_client.get_known_person_faces.return_value = [sample_face]

        runner = CliRunner()
        result = runner.invoke(cli, ["persons", "faces", "789"])

        assert result.exit_code == 0
        assert "Faces for Person ID: 789" in result.output
        assert "Total faces: 1" in result.output
        mock_store_manager.store_client.get_known_person_faces.assert_called_once_with(person_id=789)

    def test_images_similar(self, mock_store_manager, sample_similar_images_response):
        """Test images similar command."""
        mock_store_manager.store_client.find_similar_images.return_value = sample_similar_images_response

        runner = CliRunner()
        result = runner.invoke(cli, ["images", "similar", "123", "--limit", "10", "--threshold", "0.85"])

        assert result.exit_code == 0
        assert "Similar Images for Entity ID: 123" in result.output
        assert "Found 2 similar images" in result.output
        mock_store_manager.store_client.find_similar_images.assert_called_once_with(
            entity_id=123,
            limit=10,
            score_threshold=0.85,
            include_details=False,
        )

    def test_images_download_embedding(self, mock_store_manager, tmp_path):
        """Test images download-embedding command."""
        output_file = tmp_path / "entity.npy"
        mock_store_manager.store_client.download_entity_embedding.return_value = None

        runner = CliRunner()
        result = runner.invoke(cli, ["images", "download-embedding", "123", "--output", str(output_file)])

        assert result.exit_code == 0
        assert "Entity CLIP embedding downloaded" in result.output
        mock_store_manager.store_client.download_entity_embedding.assert_called_once()
