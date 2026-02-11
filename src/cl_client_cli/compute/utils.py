import click
from cl_client import SessionManager, ComputeClient
from ..common.context import CLIContext
from ..common.helper import output_error
from ..common.cached_password import save_password_to_cache, clear_password_cache

async def get_compute_client(ctx: click.Context) -> ComputeClient:
    """Get ComputeClient based on CLI context (auth or no-auth mode)."""
    context: CLIContext = ctx.obj
    username = context.username
    password = context.password
    no_auth = context.no_auth
    server_config = context.server_config
    output_json = context.output_json

    if not server_config:
        output_error(ctx, "Server configuration required.")

    # If --no-auth flag explicitly set, use no-auth mode
    if no_auth:
        return ComputeClient(
            base_url=server_config.compute_url,
            server_pref=server_config,
        )

    # If username provided but no password, prompt for it
    if username and not password:
        if output_json:
            # In JSON mode, fall back to no-auth silently
            return ComputeClient(
                base_url=server_config.compute_url,
                server_pref=server_config,
            )
        else:
            # Prompt for password interactively
            password = click.prompt("Password", hide_input=True, type=str)
            context.password = password

    # If no credentials at all, use no-auth mode
    if not (username and password):
        return ComputeClient(
            base_url=server_config.compute_url,
            server_pref=server_config,
        )

    # With credentials: create session, login, return client
    session = SessionManager(server_pref=server_config)
    try:
        await session.login(username, password)
        # Cache password after successful authentication
        if username and password:
            save_password_to_cache(username, password)
        # Store session in context for cleanup
        context.session = session
        return session.create_compute_client()
    except Exception as e:
        await session.close()
        # Clear cache on auth failure
        if username:
            clear_password_cache()
        output_error(ctx, f"Authentication failed: {e}")
