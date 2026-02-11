from typing import Optional
from pydantic import BaseModel, ConfigDict
from cl_client import ServerPref, SessionManager

class CLIContext(BaseModel):
    """Context object for CL Client CLI."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    username: Optional[str] = None
    password: Optional[str] = None
    auth_url: Optional[str] = None
    compute_url: Optional[str] = None
    store_url: Optional[str] = None
    mqtt_url: Optional[str] = None
    no_auth: bool = False
    output_json: bool = False
    server_config: Optional[ServerPref] = None
    session: Optional[SessionManager] = None
