import click
from .. import common

@click.command("logout")
@click.pass_context
def admin_logout(ctx: click.Context):
    """Logout and clear cached credentials.

    Examples:
        cl-client admin logout
    """
    common.clear_password_cache()
    if not common.should_use_json(ctx):
        click.echo("Logged out successfully", err=True)
    
    common.output_sdk_result(
        ctx, 
        common.SuccessResponse(message="Logged out successfully")
    )
