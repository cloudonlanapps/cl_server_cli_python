import os

import click
from rich.console import Console

from . import common
from .admin import admin
from .store import store
from .compute import compute
from .login import login_command
from .logout import logout_command

@click.group(cls=common.JSONGroup)
@click.version_option()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON (overrides cached config)")
@click.pass_context
def cli(ctx: click.Context, output_json: bool):
    """CL Client CLI - Command-line interface for compute, store, and auth operations.

    Login first with 'cl-client login' to cache your credentials and configuration.
    Then use commands like 'cl-client store list' or 'cl-client compute capabilities'.
    """
    # Store the JSON override flag in context for command groups to use
    ctx.ensure_object(dict)
    ctx.obj['json_override'] = output_json if output_json else None

# Register login/logout commands
cli.add_command(login_command, name="login")
cli.add_command(logout_command, name="logout")

# Register subgroups
cli.add_command(admin)
cli.add_command(store)
cli.add_command(compute)

if __name__ == "__main__":
    cli()
