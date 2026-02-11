"""Unit tests for cached config module."""

import json
import time
import tempfile
from pathlib import Path
from unittest.mock import patch
from cl_client_cli.common.cached_config import (
    _get_encryption_key,
    save_config_to_cache,
    load_config_from_cache,
    clear_config_cache,
    clear_cache,
)
from cl_client_cli.common.config import CLIConfig
from cl_client import ServerPref


def test_get_encryption_key():
    """Test encryption key generation."""
    key = _get_encryption_key()

    # Key should be consistent
    key2 = _get_encryption_key()
    assert key == key2

    # Key should be bytes
    assert isinstance(key, bytes)


def test_get_encryption_key_error_handling():
    """Test encryption key generation with uuid.getnode error."""
    with patch("cl_client_cli.common.cached_config.uuid.getnode", side_effect=Exception("UUID error")):
        key = _get_encryption_key()
        # Should still generate a key using default machine ID
        assert key is not None
        assert isinstance(key, bytes)


def test_save_and_load_config():
    """Test saving and loading config from cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_config.Path.home", return_value=Path(tmpdir)):
            # Create test config
            test_config = CLIConfig(
                server_pref=ServerPref(
                    auth_url="http://localhost:8010",
                    compute_url="http://localhost:8012",
                    store_url="http://localhost:8011",
                    mqtt_url="mqtt://localhost:1883"
                ),
                username="testuser",
                password="testpass123",
                no_auth=False,
                output_json=False
            )

            # Save config
            save_config_to_cache(test_config)

            # Verify cache file was created
            assert cache_path.exists()

            # Load config
            loaded_config = load_config_from_cache()
            assert loaded_config is not None
            assert loaded_config.username == "testuser"
            assert loaded_config.password == "testpass123"
            assert loaded_config.server_pref.auth_url == "http://localhost:8010"


def test_load_config_expired():
    """Test loading expired config returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_config.Path.home", return_value=Path(tmpdir)):
            # Create and save test config
            test_config = CLIConfig(
                server_pref=ServerPref(),
                username="testuser",
                password="testpass123"
            )
            save_config_to_cache(test_config)

            # Manually modify timestamp to simulate expiration (7 hours ago)
            with open(cache_path) as f:
                cache_data = json.load(f)
            cache_data["timestamp"] = time.time() - (7 * 3600)  # 7 hours ago
            with open(cache_path, "w") as f:
                json.dump(cache_data, f)

            # Try to load expired config
            loaded_config = load_config_from_cache()
            assert loaded_config is None

            # Cache file should be cleared
            assert not cache_path.exists()


def test_load_config_no_cache_file():
    """Test loading config when cache file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("cl_client_cli.common.cached_config.Path.home", return_value=Path(tmpdir)):
            loaded_config = load_config_from_cache()
            assert loaded_config is None


def test_load_config_corrupted_cache():
    """Test loading config from corrupted cache file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_config.Path.home", return_value=Path(tmpdir)):
            # Create corrupted cache file
            with open(cache_path, "w") as f:
                f.write("invalid json data")

            # Should handle corruption gracefully
            loaded_config = load_config_from_cache()
            assert loaded_config is None

            # Cache file should be cleared
            assert not cache_path.exists()


def test_load_config_old_format():
    """Test that old cache format is detected and cleared."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_config.Path.home", return_value=Path(tmpdir)):
            # Create cache in old format (has 'username' and 'encrypted_password')
            cache_data = {
                "username": "testuser",
                "encrypted_password": "old_encrypted_data",
                "timestamp": time.time(),
            }
            with open(cache_path, "w") as f:
                json.dump(cache_data, f)

            # Should return None and clear old format
            loaded_config = load_config_from_cache()
            assert loaded_config is None

            # Cache file should be cleared
            assert not cache_path.exists()


def test_load_config_missing_encrypted_config():
    """Test loading config when encrypted_config field is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_config.Path.home", return_value=Path(tmpdir)):
            # Create cache with missing encrypted_config
            cache_data = {
                "timestamp": time.time(),
            }
            with open(cache_path, "w") as f:
                json.dump(cache_data, f)

            # Should return None
            loaded_config = load_config_from_cache()
            assert loaded_config is None


def test_clear_config_cache():
    """Test clearing config cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_config.Path.home", return_value=Path(tmpdir)):
            # Save config
            test_config = CLIConfig(
                server_pref=ServerPref(),
                username="testuser",
                password="testpass123"
            )
            save_config_to_cache(test_config)
            assert cache_path.exists()

            # Clear cache
            clear_config_cache()
            assert not cache_path.exists()


def test_clear_config_cache_no_file():
    """Test clearing cache when file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("cl_client_cli.common.cached_config.Path.home", return_value=Path(tmpdir)):
            # Should not raise error
            clear_config_cache()


def test_clear_config_cache_permission_error():
    """Test clearing cache with permission error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_config.Path.home", return_value=Path(tmpdir)):
            # Save config
            test_config = CLIConfig(
                server_pref=ServerPref(),
                username="testuser",
                password="testpass123"
            )
            save_config_to_cache(test_config)

            # Mock unlink to raise permission error
            with patch.object(Path, "unlink", side_effect=PermissionError("Permission denied")):
                # Should handle error gracefully
                clear_config_cache()


def test_clear_cache_alias():
    """Test clear_cache is an alias for clear_config_cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_config.Path.home", return_value=Path(tmpdir)):
            # Save config
            test_config = CLIConfig(
                server_pref=ServerPref(),
                username="testuser",
                password="testpass123"
            )
            save_config_to_cache(test_config)
            assert cache_path.exists()

            # Clear using alias
            clear_cache()
            assert not cache_path.exists()


def test_save_config_write_error():
    """Test save_config handles write errors gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("cl_client_cli.common.cached_config.Path.home", return_value=Path(tmpdir)):
            # Mock open to raise error
            with patch("builtins.open", side_effect=PermissionError("Cannot write")):
                # Should not raise exception
                test_config = CLIConfig(
                    server_pref=ServerPref(),
                    username="testuser",
                    password="testpass123"
                )
                save_config_to_cache(test_config)


def test_cache_file_permissions():
    """Test that cache file is created with restricted permissions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / ".cl_client_cache"

        with patch("cl_client_cli.common.cached_config.Path.home", return_value=Path(tmpdir)):
            test_config = CLIConfig(
                server_pref=ServerPref(),
                username="testuser",
                password="testpass123"
            )
            save_config_to_cache(test_config)

            # Check file permissions (should be 600 = owner read/write only)
            mode = cache_path.stat().st_mode & 0o777
            assert mode == 0o600
