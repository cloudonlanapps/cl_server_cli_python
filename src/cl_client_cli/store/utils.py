import click
from cl_client import SessionManager, StoreManager
from ..common.context import CLIContext
from ..common.helper import output_error
from ..common.cached_password import save_password_to_cache, clear_password_cache

async def get_store_manager(ctx: click.Context) -> StoreManager:
    """Get StoreManager based on CLI context (auth or guest mode)."""
    context: CLIContext = ctx.obj
    config = context.config

    # Server config is validated by load_config, but check for safety/typing
    if not config.server_pref.store_url:
        output_error(ctx, "Server configuration required (store_url).")

    # If --no-auth flag explicitly set, use guest mode
    if config.no_auth:
        return StoreManager.guest(base_url=config.server_pref.store_url)

    # If username provided but no password, prompt for it
    if config.username and not config.password:
        if config.output_json:
            # In JSON mode, fall back to guest mode silently
            return StoreManager.guest(base_url=config.server_pref.store_url)
        else:
            # Prompt for password interactively
            password = click.prompt("Password", hide_input=True, type=str)
            config.password = password

    # If no credentials at all, use guest mode
    if not (config.username and config.password):
        return StoreManager.guest(base_url=config.server_pref.store_url)

    # With credentials: create session, login, return store manager
    server_pref = config.to_server_pref()
    session = SessionManager(server_pref=server_pref)
    try:
        assert config.username is not None, "Username required"
        assert config.password is not None, "Password required"
        
        await session.login(config.username, config.password)
        # Cache password after successful authentication
        save_password_to_cache(config.username, config.password)
        # Store session in context for cleanup
        context.session = session
        return session.create_store_manager()
    except Exception as e:
        await session.close()
        # Clear cache on auth failure
        if config.username:
            clear_password_cache()
        output_error(ctx, f"Authentication failed: {e}")
