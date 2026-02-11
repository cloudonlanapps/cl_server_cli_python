import click

@click.group(name="store")
def admin_store():
    """Store admin operations."""
    pass

# Import subcommands to register them
from .config import store_get_config
from .guest_mode import store_get_guest_mode, store_set_guest_mode
from .audit import store_audit_report
from .orphans import store_clear_orphans

admin_store.add_command(store_get_config, name="config")
admin_store.add_command(store_get_guest_mode, name="get-guest-mode")
admin_store.add_command(store_set_guest_mode, name="set-guest-mode")
admin_store.add_command(store_audit_report, name="audit-report")
admin_store.add_command(store_clear_orphans, name="clear-orphans")
