import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

class CLIConfig(BaseModel):
    """Configuration model for CL Client CLI."""
    auth_url: Optional[str] = None
    compute_url: Optional[str] = None
    store_url: Optional[str] = None
    mqtt_url: Optional[str] = None
    username: Optional[str] = None

    @classmethod
    def from_config(cls, config_path: Optional[Path] = None) -> "CLIConfig":
        """Load configuration from ~/.cl_client_config.json file."""
        if config_path is None:
            config_path = Path.home() / ".cl_client_config.json"
        
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                return cls(**data)
            except Exception:
                # Fallback to empty config on error
                pass
        
        return cls()

def load_config(config_path: Optional[Path] = None) -> CLIConfig:
    """Helper function to load config using the model's class method."""
    return CLIConfig.from_config(config_path)
