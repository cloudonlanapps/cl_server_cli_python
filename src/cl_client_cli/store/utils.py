import click
from cl_client import SessionManager, StoreManager
from ..common.context import CLIContext
from ..common.helper import output_error

async def get_store_manager(ctx: click.Context) -> StoreManager:
    """Get StoreManager based on CLI context (auth or guest mode)."""
    context: CLIContext = ctx.obj
    config = context.config

    if not config.server_pref.store_url:
        output_error(ctx, "Server configuration required (store_url).")

    # If no-auth flag set in cached config, use guest mode
    if config.no_auth:
        return StoreManager.guest(base_url=config.server_pref.store_url)

    # If no credentials, use guest mode
    if not (config.username and config.password):
        return StoreManager.guest(base_url=config.server_pref.store_url)

    # With credentials: create session, login, return store manager
    server_pref = config.to_server_pref()
    session = SessionManager(server_pref=server_pref)
    try:
        await session.login(config.username, config.password)
        context.session = session
        return session.create_store_manager()
    except Exception as e:
        await session.close()
        output_error(ctx, f"Authentication failed: {e}")
