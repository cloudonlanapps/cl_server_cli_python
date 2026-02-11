import base64
import hashlib
import json
import time
import uuid
from pathlib import Path
from cryptography.fernet import Fernet
from .config import CLIConfig


def _get_encryption_key() -> bytes:
    """Generate encryption key from machine UUID.

    Uses machine UUID only (not username) since username is in the config being encrypted.
    """
    try:
        machine_id = str(uuid.getnode())
    except Exception:
        machine_id = "default-machine"

    key_material = f"cl-client:{machine_id}".encode()
    key_hash = hashlib.sha256(key_material).digest()
    return base64.urlsafe_b64encode(key_hash)


def save_config_to_cache(config: CLIConfig) -> None:
    """Save encrypted config to cache file."""
    cache_path = Path.home() / ".cl_client_cache"
    try:
        key = _get_encryption_key()
        cipher = Fernet(key)

        # Serialize config to JSON
        config_json = config.model_dump_json()
        encrypted_config = cipher.encrypt(config_json.encode()).decode()

        cache_data = {
            "encrypted_config": encrypted_config,
            "timestamp": time.time(),
        }

        with open(cache_path, "w") as f:
            json.dump(cache_data, f)
        cache_path.chmod(0o600)
    except Exception:
        pass  # Silently fail on cache errors


def load_config_from_cache() -> CLIConfig | None:
    """Load and decrypt config from cache if not expired.

    Returns None if:
    - Cache doesn't exist
    - Cache is expired (> 6 hours)
    - Cache is corrupted or in old format
    - Decryption fails
    """
    cache_path = Path.home() / ".cl_client_cache"
    if not cache_path.exists():
        return None

    try:
        with open(cache_path) as f:
            cache_data = json.load(f)

        # Check for old format (has 'username' and 'encrypted_password')
        if "username" in cache_data or "encrypted_password" in cache_data:
            # Old format detected - clear it and return None
            clear_config_cache()
            return None

        # Check expiration (6 hours)
        timestamp = cache_data.get("timestamp", 0)
        if (time.time() - timestamp) / 3600 > 6:
            clear_config_cache()
            return None

        # Get encrypted config
        encrypted_config = cache_data.get("encrypted_config")
        if not encrypted_config:
            return None

        # Decrypt and deserialize
        key = _get_encryption_key()
        cipher = Fernet(key)
        config_json = cipher.decrypt(encrypted_config.encode()).decode()

        # Parse back to CLIConfig using Pydantic
        config = CLIConfig.model_validate_json(config_json)
        return config

    except Exception:
        # On any error, clear cache and return None
        clear_config_cache()
        return None


def clear_config_cache() -> None:
    """Clear the config cache file."""
    cache_path = Path.home() / ".cl_client_cache"
    if cache_path.exists():
        try:
            cache_path.unlink()
        except Exception:
            pass  # Silently fail


def clear_cache() -> None:
    """Alias for clear_config_cache."""
    clear_config_cache()


# Backward compatibility - deprecated but kept for migration
def clear_password_cache() -> None:
    """Deprecated: Use clear_config_cache() instead."""
    clear_config_cache()
