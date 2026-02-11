"""Unit tests for store upload command."""

from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner
from cl_client_cli.main import cli
from pathlib import Path
import tempfile


def test_upload_single_file_success(mock_store_manager, temp_image_file):
    """Test uploading a single file successfully."""
    # Mock the entity creation
    mock_entity = MagicMock()
    mock_entity.id = 1
    mock_entity.label = "test_image.jpg"

    mock_result = MagicMock()
    mock_result.is_error = False
    mock_result.data = mock_entity
    mock_result.error = None

    mock_store_manager.create_entity = AsyncMock(return_value=mock_result)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["store", "upload", str(temp_image_file), "--label", "Test Image"]
    )

    assert result.exit_code == 0
    mock_store_manager.create_entity.assert_called_once()
    call_kwargs = mock_store_manager.create_entity.call_args[1]
    assert call_kwargs["label"] == "Test Image"
    assert call_kwargs["is_collection"] is False


def test_upload_single_file_with_parent(mock_store_manager, temp_image_file):
    """Test uploading a single file with parent_id."""
    mock_entity = MagicMock()
    mock_entity.id = 1
    mock_entity.label = "test_image.jpg"

    mock_result = MagicMock()
    mock_result.is_error = False
    mock_result.data = mock_entity
    mock_result.error = None

    mock_store_manager.create_entity = AsyncMock(return_value=mock_result)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["store", "upload", str(temp_image_file), "--parent-id", "5"]
    )

    assert result.exit_code == 0
    call_kwargs = mock_store_manager.create_entity.call_args[1]
    assert call_kwargs["parent_id"] == 5


def test_upload_directory_without_recursive(mock_store_manager):
    """Test uploading a directory without --recursive flag should fail."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(
            cli,
            ["store", "upload", tmpdir]
        )

        # Should error because directory needs --recursive
        assert result.exit_code != 0
        assert "recursive" in result.output.lower() or "directory" in result.output.lower()


def test_upload_directory_recursive_success(mock_store_manager):
    """Test uploading a directory with --recursive and --yes flags."""
    # Create temporary directory with test images
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create test image files
        img1 = tmppath / "photo1.jpg"
        img2 = tmppath / "photo2.png"
        img1.write_text("fake image data")
        img2.write_text("fake image data")

        # Mock successful uploads
        mock_entity = MagicMock()
        mock_entity.id = 1

        mock_result = MagicMock()
        mock_result.is_error = False
        mock_result.data = mock_entity
        mock_result.error = None

        mock_store_manager.create_entity = AsyncMock(return_value=mock_result)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["store", "upload", tmpdir, "--recursive", "--yes"]
        )

        assert result.exit_code == 0
        # Should have uploaded 2 files
        assert mock_store_manager.create_entity.call_count == 2


def test_upload_directory_recursive_with_subdirs(mock_store_manager):
    """Test uploading a directory recursively includes subdirectories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create nested structure
        subdir = tmppath / "subdir"
        subdir.mkdir()

        img1 = tmppath / "photo1.jpg"
        img2 = subdir / "photo2.jpg"
        img1.write_text("fake image data")
        img2.write_text("fake image data")

        mock_entity = MagicMock()
        mock_entity.id = 1

        mock_result = MagicMock()
        mock_result.is_error = False
        mock_result.data = mock_entity
        mock_result.error = None

        mock_store_manager.create_entity = AsyncMock(return_value=mock_result)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["store", "upload", tmpdir, "--recursive", "--yes"]
        )

        assert result.exit_code == 0
        # Should find both images including in subdirectory
        assert mock_store_manager.create_entity.call_count == 2


def test_upload_directory_empty(mock_store_manager):
    """Test uploading an empty directory should fail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["store", "upload", tmpdir, "--recursive", "--yes"]
        )

        # Should error because no images found
        assert result.exit_code != 0
        assert "no image" in result.output.lower() or "not found" in result.output.lower()
