import click
from . import common


@click.command("logout")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def logout_command(output_json: bool):
    """Clear cached configuration and credentials.

    Examples:
        cl-client logout
    """
    common.clear_config_cache()

    if output_json:
        click.echo('{"status": "success", "message": "Logged out successfully"}')
    else:
        click.echo("✓ Logged out successfully", err=True)
        click.echo("  Cached config cleared", err=True)
