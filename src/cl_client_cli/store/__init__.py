import click
from .. import common
from .utils import get_store_manager

@click.group(cls=common.JSONGroup)
def store():
    """Store operations - manage media entities and collections."""
    pass

__all__ = ["store", "get_store_manager"]

# Import subcommands to register them
from .list import list_entities
from .upload import upload_entity
from .create import create_entity
from .get import get_entity
from .update import update_entity
from .patch import patch_entity
from .delete import delete_entity
from .versions import get_versions
from .face import face
from .intelligence import get_intelligence

store.add_command(list_entities, name="list")
store.add_command(upload_entity, name="upload")
store.add_command(create_entity, name="create")
store.add_command(get_entity, name="get")
store.add_command(update_entity, name="update")
store.add_command(patch_entity, name="patch")
store.add_command(delete_entity, name="delete")
store.add_command(get_versions, name="versions")
store.add_command(face)
store.add_command(get_intelligence, name="intelligence")
