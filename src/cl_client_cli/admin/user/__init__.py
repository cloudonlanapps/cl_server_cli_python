import click
@click.group()
def user():
    """Admin user operations."""
    pass

# Import subcommands to register them
from .create import create_user
from .list import list_users
from .get import get_user
from .update import update_user
from .delete import delete_user
from .permissions import permissions_group

user.add_command(create_user, name="create")
user.add_command(list_users, name="list")
user.add_command(get_user, name="get")
user.add_command(update_user, name="update")
user.add_command(delete_user, name="delete")
user.add_command(permissions_group)
