"""Shared test fixtures for CLI tests."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cl_client.models import JobResponse
from cl_client.store_models import (
    Entity,
    EntityListResponse,
    EntityPagination,
    EntityVersion,
    StoreConfig,
)

# ============================================================================
# TEST ARTIFACT DIRECTORY
# ============================================================================

TEST_ARTIFACT_DIR = Path(os.getenv("TEST_ARTIFACT_DIR", "/tmp/cl_server_test_artifacts")) / "cli_python"
TEST_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def temp_image_file(tmp_path: Path) -> Path:
    """Create a temporary image file for testing."""
    image_file = tmp_path / "test_image.jpg"
    image_file.write_bytes(b"fake image data")
    return image_file


@pytest.fixture
def temp_video_file(tmp_path: Path) -> Path:
    """Create a temporary video file for testing."""
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"fake video data")
    return video_file


@pytest.fixture
def mock_compute_client():
    """Create a mock ComputeClient for CLI testing."""
    with patch("cl_client_cli.main.ComputeClient") as mock_client_class:
        # Create mock client instance
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.close = AsyncMock(return_value=None)
        mock_client.download_job_file = AsyncMock(return_value=None)

        # Mock plugin clients
        mock_client.clip_embedding = MagicMock()
        mock_client.dino_embedding = MagicMock()
        mock_client.exif = MagicMock()
        mock_client.face_detection = MagicMock()
        mock_client.face_embedding = MagicMock()
        mock_client.hash = MagicMock()
        mock_client.hls_streaming = MagicMock()
        mock_client.image_conversion = MagicMock()
        mock_client.media_thumbnail = MagicMock()

        # Configure the class to return our mock instance
        mock_client_class.return_value = mock_client

        yield mock_client


@pytest.fixture
def completed_job() -> JobResponse:
    """Create a completed job response."""
    return JobResponse(
        job_id="test-job-123",
        task_type="clip_embedding",
        status="completed",
        progress=100,
        params={},
        task_output={"embedding": [0.1] * 512},
        priority=5,
        created_at=1234567890000,
        completed_at=1234567891000,
    )


@pytest.fixture
def queued_job() -> JobResponse:
    """Create a queued job response."""
    return JobResponse(
        job_id="test-job-123",
        task_type="clip_embedding",
        status="queued",
        progress=0,
        params={},
        priority=5,
        created_at=1234567890000,
    )


@pytest.fixture
def failed_job() -> JobResponse:
    """Create a failed job response."""
    return JobResponse(
        job_id="test-job-123",
        task_type="clip_embedding",
        status="failed",
        progress=50,
        params={},
        error_message="Test error",
        priority=5,
        created_at=1234567890000,
        completed_at=1234567891000,
    )


# Store-related fixtures


@pytest.fixture
def mock_store_manager():
    """Create a mock StoreManager for CLI testing."""
    with patch("cl_client_cli.main.StoreManager") as mock_manager_class:
        # Create mock manager instance
        mock_manager = MagicMock()
        mock_manager.__aenter__ = AsyncMock(return_value=mock_manager)
        mock_manager.__aexit__ = AsyncMock(return_value=None)

        # Mock all StoreManager methods to return success results
        mock_manager.list_entities = AsyncMock()
        mock_manager.read_entity = AsyncMock()
        mock_manager.create_entity = AsyncMock()
        mock_manager.update_entity = AsyncMock()
        mock_manager.patch_entity = AsyncMock()
        mock_manager.delete_entity = AsyncMock()
        mock_manager.get_versions = AsyncMock()
        mock_manager.get_config = AsyncMock()
        mock_manager.update_guest_mode = AsyncMock()

        # Mock _store_client for database methods
        mock_store_client = MagicMock()
        mock_store_client.__aexit__ = AsyncMock(return_value=None)


        # Configure the class methods
        mock_manager_class.guest = MagicMock(return_value=mock_manager)
        mock_manager_class.authenticated = MagicMock(return_value=mock_manager)

        yield mock_manager


@pytest.fixture
def sample_entity() -> Entity:
    """Create a sample entity."""
    return Entity(
        id=1,
        label="Test Entity",
        description="Test description",
        is_collection=False,
        file_size=1024,
        mime_type="image/jpeg",
        file_path="/media/test.jpg",
    )


@pytest.fixture
def sample_collection() -> Entity:
    """Create a sample collection entity."""
    return Entity(
        id=2,
        label="Test Collection",
        description="Test collection",
        is_collection=True,
    )


@pytest.fixture
def sample_entity_list() -> EntityListResponse:
    """Create a sample entity list response."""
    return EntityListResponse(
        items=[
            Entity(id=1, label="Entity 1", is_collection=False),
            Entity(id=2, label="Entity 2", is_collection=True),
        ],
        pagination=EntityPagination(
            page=1,
            page_size=20,
            total_items=2,
            total_pages=1,
            has_next=False,
            has_prev=False,
        ),
    )


@pytest.fixture
def sample_versions() -> list[EntityVersion]:
    """Create sample entity versions."""
    return [
        EntityVersion(
            version=1,
            transaction_id=100,
            operation_type="INSERT",
            label="Version 1",
        ),
        EntityVersion(
            version=2,
            transaction_id=101,
            operation_type="UPDATE",
            label="Version 2",
        ),
    ]


@pytest.fixture
def sample_store_config() -> StoreConfig:
    """Create a sample store config."""
    return StoreConfig(
        guest_mode=False,
        updated_at=1704067200000,
        updated_by="admin",
    )



