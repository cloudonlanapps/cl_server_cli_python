"""Unit tests for cached password module."""

import json
import time
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from cl_client_cli.common.cached_password import (
    _get_encryption_key,
    save_password_to_cache,
    load_password_from_cache,
    clear_password_cache,
    clear_cache,
)


def test_get_encryption_key():
    """Test encryption key generation."""
    key = _get_encryption_key("testuser")

    # Key should be consistent for same username
    key2 = _get_encryption_key("testuser")
    assert key == key2

    # Different username should generate different key
    key3 = _get_encryption_key("otheruser")
    assert key != key3


def test_get_encryption_key_error_handling():
    """Test encryption key generation with uuid.getnode error."""
    with patch("cl_client_cli.common.cached_password.uuid.getnode", side_effect=Exception("UUID error")):
        key = _get_encryption_key("testuser")
        # Should still generate a key using default machine ID
        assert key is not None
        assert isinstance(key, bytes)


def test_save_and_load_password():
    """Test saving and loading password from cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_password.Path.home", return_value=Path(tmpdir)):
            # Save password
            save_password_to_cache("testuser", "testpass123")

            # Verify cache file was created
            assert cache_path.exists()

            # Load password
            loaded_password = load_password_from_cache("testuser")
            assert loaded_password == "testpass123"


def test_load_password_different_username():
    """Test loading password with different username returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("cl_client_cli.common.cached_password.Path.home", return_value=Path(tmpdir)):
            # Save password for one user
            save_password_to_cache("user1", "password1")

            # Try to load with different username
            loaded_password = load_password_from_cache("user2")
            assert loaded_password is None


def test_load_password_expired():
    """Test loading expired password returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_password.Path.home", return_value=Path(tmpdir)):
            # Save password
            save_password_to_cache("testuser", "testpass123")

            # Manually modify timestamp to simulate expiration (7 hours ago)
            with open(cache_path) as f:
                cache_data = json.load(f)
            cache_data["timestamp"] = time.time() - (7 * 3600)  # 7 hours ago
            with open(cache_path, "w") as f:
                json.dump(cache_data, f)

            # Try to load expired password
            loaded_password = load_password_from_cache("testuser")
            assert loaded_password is None

            # Cache file should be cleared
            assert not cache_path.exists()


def test_load_password_no_cache_file():
    """Test loading password when cache file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("cl_client_cli.common.cached_password.Path.home", return_value=Path(tmpdir)):
            loaded_password = load_password_from_cache("testuser")
            assert loaded_password is None


def test_load_password_corrupted_cache():
    """Test loading password from corrupted cache file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_password.Path.home", return_value=Path(tmpdir)):
            # Create corrupted cache file
            with open(cache_path, "w") as f:
                f.write("invalid json data")

            # Should handle corruption gracefully
            loaded_password = load_password_from_cache("testuser")
            assert loaded_password is None

            # Cache file should be cleared
            assert not cache_path.exists()


def test_load_password_missing_encrypted_password():
    """Test loading password when encrypted_password field is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_password.Path.home", return_value=Path(tmpdir)):
            # Create cache with missing encrypted_password
            cache_data = {
                "username": "testuser",
                "timestamp": time.time(),
            }
            with open(cache_path, "w") as f:
                json.dump(cache_data, f)

            # Should return None
            loaded_password = load_password_from_cache("testuser")
            assert loaded_password is None


def test_clear_password_cache():
    """Test clearing password cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_password.Path.home", return_value=Path(tmpdir)):
            # Save password
            save_password_to_cache("testuser", "testpass123")
            assert cache_path.exists()

            # Clear cache
            clear_password_cache()
            assert not cache_path.exists()


def test_clear_password_cache_no_file():
    """Test clearing cache when file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("cl_client_cli.common.cached_password.Path.home", return_value=Path(tmpdir)):
            # Should not raise error
            clear_password_cache()


def test_clear_password_cache_permission_error():
    """Test clearing cache with permission error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_password.Path.home", return_value=Path(tmpdir)):
            # Save password
            save_password_to_cache("testuser", "testpass123")

            # Mock unlink to raise permission error
            with patch.object(Path, "unlink", side_effect=PermissionError("Permission denied")):
                # Should handle error gracefully
                clear_password_cache()


def test_clear_cache_alias():
    """Test clear_cache is an alias for clear_password_cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_password.Path.home", return_value=Path(tmpdir)):
            # Save password
            save_password_to_cache("testuser", "testpass123")
            assert cache_path.exists()

            # Clear using alias
            clear_cache()
            assert not cache_path.exists()


def test_save_password_write_error():
    """Test save_password handles write errors gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_password.Path.home", return_value=Path(tmpdir)):
            # Mock open to raise error
            with patch("builtins.open", side_effect=PermissionError("Cannot write")):
                # Should not raise exception
                save_password_to_cache("testuser", "testpass123")


def test_cache_file_permissions():
    """Test that cache file is created with restricted permissions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_password.Path.home", return_value=Path(tmpdir)):
            save_password_to_cache("testuser", "testpass123")

            # Check file permissions (should be 600 = owner read/write only)
            mode = cache_path.stat().st_mode & 0o777
            assert mode == 0o600
