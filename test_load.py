import sys
from cl_client_cli.common.cached_config import load_config_from_cache

try:
    c = load_config_from_cache()
    if c is None:
        print("None returned")
    else:
        print("Loaded config:", c.username)
except Exception as e:
    import traceback
    traceback.print_exc()

