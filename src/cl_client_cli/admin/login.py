import asyncio
import click
from .. import common
from ..common.context import CLIContext

@click.command("login")
@click.option("--username", "-u", help="Username")
@click.option("--password", "-p", help="Password")
@click.pass_context
def admin_login(ctx: click.Context, username: str | None, password: str | None):
    """Login and cache credentials for subsequent commands.

    Username and password are optional - they can be taken from:
    - CLI flags (highest priority)
    - Config file (~/.cl_client_config.ini)
    - Interactive prompt (for password only)

    Examples:
        cl-client admin login
        cl-client admin login -u admin -p pass123
    """
    context: CLIContext = ctx.obj
    # Merge context with explicit flags
    if username:
        context.username = username
    if password:
        context.password = password

    async def run():
        session = await common.get_session_manager(ctx)
        try:
            # get_session_manager already handles login and caching
            if not common.should_use_json(ctx):
                click.echo(f"Successfully logged in as {context.username}", err=True)
            
            # Simple success response for JSON
            common.output_sdk_result(
                ctx, 
                common.SuccessResponse(message=f"Logged in as {context.username}")
            )
        except Exception as e:
            common.output_error(ctx, str(e))
        finally:
            await session.close()

    asyncio.run(run())
