import sys
from cl_client_cli.common.cached_config import save_config_to_cache
from cl_client_cli.common.config import CLIConfig
from cl_client import ServerPref

try:
    c = CLIConfig(server_pref=ServerPref())
    save_config_to_cache(c)
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()

