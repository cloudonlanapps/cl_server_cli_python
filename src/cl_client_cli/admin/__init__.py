import click
from .. import common


@click.group()
@click.pass_context
def admin(ctx: click.Context):
    """Admin operations (requires authentication)."""
    # Load cached config before any admin command runs
    context = common.load_cached_config_or_exit(ctx)

    # Apply JSON override from root CLI if present
    if ctx.parent and ctx.parent.obj and 'json_override' in ctx.parent.obj:
        if ctx.parent.obj['json_override']:
            context.config.output_json = True

    ctx.obj = context

# Import sub-packages to register them
from .user import user
from .store import admin_store
from .compute import admin_compute

admin.add_command(user)
admin.add_command(admin_store)
admin.add_command(admin_compute)
