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
from .cached_config import load_config_from_cache
from .config import CLIConfig

def should_use_json(ctx: click.Context) -> bool:
    """Check if JSON output is enabled."""
    context: CLIContext = ctx.obj
    return context.config.output_json

def load_cached_config_or_exit(ctx: click.Context) -> CLIContext:
    """Load config from cache or exit with error.

    This is called by command group callbacks to ensure users are logged in.
    """
    config = load_config_from_cache()
    if config is None:
        click.echo(
            "Error: Not logged in. Please run: cl-client login --help",
            err=True
        )
        ctx.exit(1)

    return CLIContext(config=config)

async def get_session_manager(ctx: click.Context) -> SessionManager:
    """Get authenticated SessionManager from context config."""
    context: CLIContext = ctx.obj
    config = context.config

    if not config.username or not config.password:
        output_error(ctx, "Authentication required. Please run: cl-client login")

    server_pref = config.to_server_pref()
    session = SessionManager(server_pref=server_pref)

    try:
        await session.login(config.username, config.password)
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
