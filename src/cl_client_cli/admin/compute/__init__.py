import click

@click.group(name="compute")
def admin_compute():
    """Compute admin operations."""
    pass

# Import subcommands to register them
from .capabilities import capabilities
from .guest_mode import guest_mode

admin_compute.add_command(capabilities)
admin_compute.add_command(guest_mode)
