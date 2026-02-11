import click
from cl_client import SessionManager, ComputeClient
from ..common.context import CLIContext
from ..common.helper import output_error
from ..common.cached_password import save_password_to_cache, clear_password_cache

async def get_compute_client(ctx: click.Context) -> ComputeClient:
    """Get ComputeClient based on CLI context (auth or no-auth mode)."""
    context: CLIContext = ctx.obj
    config = context.config

    if not config.server_pref.compute_url:
        output_error(ctx, "Server configuration required (compute_url).")

    server_pref = config.to_server_pref()

    # If --no-auth flag explicitly set, use no-auth mode
    if config.no_auth:
        return ComputeClient(
            base_url=config.server_pref.compute_url,
            server_pref=server_pref,
        )

    # If username provided but no password, prompt for it
    if config.username and not config.password:
        if config.output_json:
            # In JSON mode, fall back to no-auth silently
            return ComputeClient(
                base_url=config.server_pref.compute_url,
                server_pref=server_pref,
            )
        else:
            # Prompt for password interactively
            password = click.prompt("Password", hide_input=True, type=str)
            config.password = password

    # If no credentials at all, use no-auth mode
    if not (config.username and config.password):
        return ComputeClient(
            base_url=config.server_pref.compute_url,
            server_pref=server_pref,
        )

    # With credentials: create session, login, return client
    session = SessionManager(server_pref=server_pref)
    try:
        assert config.username is not None, "Username required"
        assert config.password is not None, "Password required"
        
        await session.login(config.username, config.password)
        # Cache password after successful authentication
        save_password_to_cache(config.username, config.password)
        # Store session in context for cleanup
        context.session = session
        return session.create_compute_client()
    except Exception as e:
        await session.close()
        # Clear cache on auth failure
        if config.username:
            clear_password_cache()
        output_error(ctx, f"Authentication failed: {e}")
