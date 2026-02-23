import sys
import json
import time
from pathlib import Path
from cryptography.fernet import Fernet
from cl_client_cli.common.cached_config import _get_encryption_key
from cl_client_cli.common.config import CLIConfig

cache_path = Path.home() / ".cl_client_cache"

if not cache_path.exists():
    print("Cache does not exist")
    sys.exit(1)

with open(cache_path) as f:
    cache_data = json.load(f)

print("Keys in cache_data:", list(cache_data.keys()))

if "username" in cache_data or "encrypted_password" in cache_data:
    print("Old format detected")

timestamp = cache_data.get("timestamp", 0)
print("Hours old:", (time.time() - timestamp) / 3600)

encrypted_config = cache_data.get("encrypted_config")
if not encrypted_config:
    print("No encrypted_config")

try:
    key = _get_encryption_key()
    cipher = Fernet(key)
    config_json = cipher.decrypt(encrypted_config.encode()).decode()
    print("Decrypted json type:", type(config_json))
    config = CLIConfig.model_validate_json(config_json)
    print("Successfully parsed CLIConfig")
except Exception as e:
    import traceback
    traceback.print_exc()

