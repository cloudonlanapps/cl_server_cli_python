from typing import Optional
from pydantic import BaseModel, ConfigDict
from cl_client import SessionManager
from .config import CLIConfig

class CLIContext(BaseModel):
    """Context object for CL Client CLI.
    
    Holds the runtime configuration and active session.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    config: CLIConfig
    session: Optional[SessionManager] = None
