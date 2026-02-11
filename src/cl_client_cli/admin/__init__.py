import click


@click.group()
def admin():
    """Admin operations."""
    pass

# Import sub-packages to register them
from .user import user
from .store import admin_store
from .compute import admin_compute
from .login import admin_login
from .logout import admin_logout

admin.add_command(user)
admin.add_command(admin_store)
admin.add_command(admin_compute)
admin.add_command(admin_login, name="login")
admin.add_command(admin_logout, name="logout")
