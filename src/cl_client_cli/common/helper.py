import sys
from typing import Any, NoReturn
import click
from pydantic import BaseModel
from rich.console import Console
from .context import CLIContext

console = Console()

class ErrorResponse(BaseModel):
    """CLI error response model."""
    error: str
    status: str = "failed"

class SuccessResponse(BaseModel):
    """CLI success response model for void operations."""
    status: str = "success"
    message: str | None = None

class CLIException(click.ClickException):
    """Custom exception for CLI errors with support for JSON formatting."""
    def __init__(self, ctx: click.Context, message: str):
        super().__init__(message)
        self.ctx = ctx

    def show(self, file: Any | None = None) -> None:
        """Format and display the error message."""
        error = ErrorResponse(error=self.message)
        if should_use_json(self.ctx):
            click.echo(error.model_dump_json(indent=2))
        else:
            # Human mode: just print error message to stderr
            click.echo(f"Error: {self.message}", err=True)

class JSONGroup(click.Group):
    """Custom Click Group to handle exceptions as JSON when --json flag is present."""

    def main(self, *args: Any, **kwargs: Any) -> Any:
        cmd_args = kwargs.get("args")
        if cmd_args is None and len(args) > 0:
            cmd_args = args[0]
        
        original_standalone_mode = kwargs.get("standalone_mode", True)
        kwargs["standalone_mode"] = False

        try:
            return super().main(*args, **kwargs)
        except click.ClickException as e:
            use_json = False
            if cmd_args is not None:
                use_json = "--json" in cmd_args
            else:
                use_json = "--json" in sys.argv
            
            if use_json:
                error = ErrorResponse(error=str(e), status="failed")
                click.echo(error.model_dump_json(indent=2))
                sys.exit(e.exit_code)
            else:
                if original_standalone_mode:
                    e.show()
                    sys.exit(e.exit_code)
                else:
                    raise

from cl_client import SessionManager
from .cached_password import save_password_to_cache

def should_use_json(ctx: click.Context) -> bool:
    """Check if JSON output is enabled."""
    context: CLIContext = ctx.obj
    return context.config.output_json

async def get_session_manager(ctx: click.Context) -> SessionManager:
    """Get authenticated SessionManager for admin operations."""
    context: CLIContext = ctx.obj
    config = context.config
    
    # Check credentials in config
    if not (config.username and config.password):
        if config.output_json:
            output_error(ctx, "Credentials required in config block for JSON mode")
        else:
            username = config.username or click.prompt("Username", type=str)
            password = config.password or click.prompt("Password", hide_input=True, type=str)
            # Update config with prompted values (in memory only)
            config.username = username
            config.password = password

    # Server config is now guaranteed by load_config validation
    if not config.server_pref.auth_url:
         output_error(ctx, "Server configuration required.")

    # Convert CLIConfig to ServerPref
    server_pref = config.to_server_pref()

    session = SessionManager(server_pref=server_pref)
    try:
        # We ensured credentials are set above
        assert config.username is not None
        assert config.password is not None
        
        await session.login(config.username, config.password)
        # Cache password after successful authentication
        save_password_to_cache(config.username, config.password)
        # Store session in context for cleanup
        context.session = session
        return session
    except Exception as e:
        await session.close()
        output_error(ctx, f"Authentication failed: {e}")

def output_sdk_result(ctx: click.Context, sdk_model: BaseModel) -> None:
    """Output SDK Pydantic model directly."""
    click.echo(sdk_model.model_dump_json(indent=2, exclude_none=True))

def output_error(ctx: click.Context, error_message: str) -> NoReturn:
    """Output CLI error via custom exception."""
    raise CLIException(ctx, error_message)

def print_job_result(ctx: click.Context, job: Any) -> None:
    """Print job result using SDK JobResponse model."""
    output_sdk_result(ctx, job)
