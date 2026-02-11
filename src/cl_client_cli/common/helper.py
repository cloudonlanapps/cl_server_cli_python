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
    return context.output_json

async def get_session_manager(ctx: click.Context) -> SessionManager:
    """Get authenticated SessionManager for admin operations."""
    context: CLIContext = ctx.obj
    username = context.username
    password = context.password
    server_config = context.server_config
    output_json = context.output_json

    if not (username and password):
        if output_json:
            output_error(ctx, "Credentials required in config block for JSON mode")
        else:
            username = username or click.prompt("Username", type=str)
            password = password or click.prompt("Password", hide_input=True, type=str)
            # Update context with prompted values
            context.username = username
            context.password = password

    if not server_config:
        output_error(ctx, "Server configuration required.")

    session = SessionManager(server_pref=server_config)
    try:
        await session.login(username, password)
        # Cache password after successful authentication
        if username and password:
            save_password_to_cache(username, password)
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
