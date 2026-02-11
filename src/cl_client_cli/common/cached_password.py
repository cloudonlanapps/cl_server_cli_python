import base64
import hashlib
import json
import time
import uuid
from pathlib import Path
from cryptography.fernet import Fernet

def _get_encryption_key(username: str) -> bytes:
    """Generate encryption key from username and machine UUID."""
    try:
        machine_id = str(uuid.getnode())
    except Exception:
        machine_id = "default-machine"

    key_material = f"{username}:{machine_id}".encode()
    key_hash = hashlib.sha256(key_material).digest()
    return base64.urlsafe_b64encode(key_hash)

def save_password_to_cache(username: str, password: str) -> None:
    """Save encrypted password to cache file."""
    cache_path = Path.home() / ".cl_client_cache"
    try:
        key = _get_encryption_key(username)
        cipher = Fernet(key)
        encrypted_password = cipher.encrypt(password.encode()).decode()
        cache_data = {
            "username": username,
            "encrypted_password": encrypted_password,
            "timestamp": time.time(),
        }
        with open(cache_path, "w") as f:
            json.dump(cache_data, f)
        cache_path.chmod(0o600)
    except Exception:
        pass

def load_password_from_cache(username: str) -> str | None:
    """Load and decrypt password from cache if not expired."""
    cache_path = Path.home() / ".cl_client_cache"
    if not cache_path.exists():
        return None
    try:
        with open(cache_path) as f:
            cache_data = json.load(f)
        cached_username = cache_data.get("username")
        if cached_username != username:
            return None
        timestamp = cache_data.get("timestamp", 0)
        # Cache expires in 6 hours
        if (time.time() - timestamp) / 3600 > 6:
            clear_password_cache()
            return None
        encrypted_password = cache_data.get("encrypted_password")
        if not encrypted_password:
            return None
        key = _get_encryption_key(username)
        cipher = Fernet(key)
        return cipher.decrypt(encrypted_password.encode()).decode()
    except Exception:
        clear_password_cache()
        return None

def clear_password_cache() -> None:
    """Clear the password cache file."""
    cache_path = Path.home() / ".cl_client_cache"
    if cache_path.exists():
        try:
            cache_path.unlink()
        except Exception:
            pass

def clear_cache() -> None:
    """Alias for clear_password_cache."""
    clear_password_cache()
