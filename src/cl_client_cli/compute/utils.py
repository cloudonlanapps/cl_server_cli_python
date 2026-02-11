import click
from cl_client import SessionManager, ComputeClient
from ..common.context import CLIContext
from ..common.helper import output_error

async def get_compute_client(ctx: click.Context) -> ComputeClient:
    """Get ComputeClient based on CLI context (auth or no-auth mode)."""
    context: CLIContext = ctx.obj
    config = context.config

    if not config.server_pref.compute_url:
        output_error(ctx, "Server configuration required (compute_url).")

    server_pref = config.to_server_pref()

    # If no-auth flag set in cached config, use no-auth mode
    if config.no_auth:
        return ComputeClient(
            base_url=config.server_pref.compute_url,
            server_pref=server_pref,
        )

    # If no credentials, use no-auth mode
    if not (config.username and config.password):
        return ComputeClient(
            base_url=config.server_pref.compute_url,
            server_pref=server_pref,
        )

    # With credentials: create session, login, return client
    session = SessionManager(server_pref=server_pref)
    try:
        await session.login(config.username, config.password)
        context.session = session
        return session.create_compute_client()
    except Exception as e:
        await session.close()
        output_error(ctx, f"Authentication failed: {e}")
