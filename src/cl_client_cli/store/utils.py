import click
from cl_client import SessionManager, StoreManager
from ..common.context import CLIContext
from ..common.helper import output_error
from ..common.cached_password import save_password_to_cache, clear_password_cache

async def get_store_manager(ctx: click.Context) -> StoreManager:
    """Get StoreManager based on CLI context (auth or guest mode)."""
    context: CLIContext = ctx.obj
    username = context.username
    password = context.password
    no_auth = context.no_auth
    server_config = context.server_config
    output_json = context.output_json

    if not server_config:
        output_error(ctx, "Server configuration required.")

    # If --no-auth flag explicitly set, use guest mode
    if no_auth:
        return StoreManager.guest(base_url=server_config.store_url)

    # If username provided but no password, prompt for it
    if username and not password:
        if output_json:
            # In JSON mode, fall back to guest mode silently
            return StoreManager.guest(base_url=server_config.store_url)
        else:
            # Prompt for password interactively
            password = click.prompt("Password", hide_input=True, type=str)
            context.password = password

    # If no credentials at all, use guest mode
    if not (username and password):
        return StoreManager.guest(base_url=server_config.store_url)

    # With credentials: create session, login, return store manager
    session = SessionManager(server_pref=server_config)
    try:
        await session.login(username, password)
        # Cache password after successful authentication
        if username and password:
            save_password_to_cache(username, password)
        # Store session in context for cleanup
        context.session = session
        return session.create_store_manager()
    except Exception as e:
        await session.close()
        # Clear cache on auth failure
        if username:
            clear_password_cache()
        output_error(ctx, f"Authentication failed: {e}")
