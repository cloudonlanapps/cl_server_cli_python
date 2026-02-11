import os

import click
from rich.console import Console

from cl_client import ServerPref
from . import common
from .common.config import load_config
from .common.context import CLIContext
from .admin import admin
from .store import store
from .compute import compute

@click.group(cls=common.JSONGroup)
@click.version_option()
@click.option(
    "--username",
    help="Username for authentication",
)
@click.option(
    "--password",
    help="Password for authentication",
)
@click.option(
    "--auth-url",
    help="Auth service URL (can be set in config file)",
)
@click.option(
    "--compute-url",
    help="Compute service URL (can be set in config file)",
)
@click.option(
    "--store-url",
    help="Store service URL (can be set in config file)",
)
@click.option(
    "--mqtt-url",
    help="MQTT broker URL (can be set in config file)",
)
@click.option(
    "--no-auth",
    is_flag=True,
    default=False,
    help="Disable authentication (use no-auth mode)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Output results as JSON (script-friendly)",
)
@click.pass_context
def cli(
    ctx: click.Context,
    username: str | None,
    password: str | None,
    auth_url: str | None,
    compute_url: str | None,
    store_url: str | None,
    mqtt_url: str | None,
    no_auth: bool,
    output_json: bool,
):
    """CL Client CLI - Command-line interface for compute, store, and auth operations.

    Configuration priority (highest to lowest):
      1. Command-line options
      2. Config file (~/.cl_client_config.ini)
    """
    # Suppress Rich console output in JSON mode to ensure clean JSON stdout
    if output_json:
        common.console = Console(file=open(os.devnull, "w"))

    # Load config file (CLIConfig Pydantic model)
    config = load_config()

    # Priority: CLI flags > config file
    auth_url = auth_url or config.auth_url
    compute_url = compute_url or config.compute_url
    store_url = store_url or config.store_url
    mqtt_url = mqtt_url or config.mqtt_url
    username = username or config.username

    # Try to load cached password if username provided but no password
    if username and not password and not no_auth:
        cached_password = common.load_password_from_cache(username)
        if cached_password:
            password = cached_password
            if not output_json:
                click.echo("Using cached password", err=True)

    # Initialize CLIContext Pydantic model
    context = CLIContext(
        username=username,
        password=password,
        auth_url=auth_url,
        compute_url=compute_url,
        store_url=store_url,
        mqtt_url=mqtt_url,
        no_auth=no_auth,
        output_json=output_json,
    )

    # Only create ServerPref if we have all URLs
    if auth_url and compute_url and store_url and mqtt_url:
        context.server_config = ServerPref(
            auth_url=auth_url,
            compute_url=compute_url,
            store_url=store_url,
            mqtt_url=mqtt_url,
        )
    
    # Set the structured context
    ctx.obj = context

# Register subgroups
cli.add_command(admin)
cli.add_command(store)
cli.add_command(compute)

if __name__ == "__main__":
    cli()
