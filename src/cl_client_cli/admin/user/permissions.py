import click
import json
from pydantic import BaseModel
from ... import common

# ============================================================================
# Permissions Configuration (Merged from auth/permissions.py)
# ============================================================================

ALLOWED_PERMISSIONS: list[str] = [
    "read:jobs",
    "write:jobs",
    "delete:jobs",
    "read:entities",
    "write:entities",
    "delete:entities",
    "admin:users",
    "admin:config",
    "admin:system",
]

class PermissionsList(BaseModel):
    permissions: list[str]
    count: int

class Permissions:
    @classmethod
    def validate(cls, permissions: tuple[str, ...]) -> tuple[bool, list[str]]:
        """Validate permissions against allowed list.

        Args:
            permissions: Tuple of permission strings to validate

        Returns:
            Tuple of (is_valid, list_of_invalid_permissions)
        """
        invalid = [p for p in permissions if p not in ALLOWED_PERMISSIONS]
        return (len(invalid) == 0, invalid)

    @classmethod
    def get_all(cls) -> PermissionsList:
        return PermissionsList(
            permissions=ALLOWED_PERMISSIONS,
            count=len(ALLOWED_PERMISSIONS),
        )

# ============================================================================
# Permissions Commands (Merged from admin/permissions_group.py)
# ============================================================================

@click.group("permissions")
def permissions_group():
    """Permissions management commands."""
    pass

@permissions_group.command("list")
@click.pass_context
def permissions_list(ctx: click.Context):
    """List all allowed permissions.

    Examples:
        cl-client admin user permissions list
    """
    perms = Permissions.get_all()
    if common.should_use_json(ctx):
        click.echo(json.dumps(perms.model_dump(), indent=2))
    else:
        click.echo("Allowed permissions:")
        for p in perms.permissions:
            click.echo(f"  - {p}")
