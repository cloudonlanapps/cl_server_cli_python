import asyncio
import click
from cl_client import UserUpdateRequest
from ... import common
from .permissions import Permissions

@click.command("update")
@click.argument("user_id", type=int)
@click.option("--password", help="New password")
@click.option("--admin/--no-admin", default=None, help="Grant/revoke admin privileges")
@click.option("--active/--inactive", default=None, help="Activate/deactivate user")
@click.option(
    "--permissions",
    "-p",
    multiple=True,
    help="Permissions to grant (replaces existing permissions)",
)
@click.pass_context
def update_user(
    ctx: click.Context,
    user_id: int,
    password: str | None,
    admin: bool | None,
    active: bool | None,
    permissions: tuple[str, ...],
):
    """Update user (admin only).

    Examples:
        cl-client admin user update 2 --password newpass123
        cl-client admin user update 2 --admin
        cl-client admin user update 2 --inactive
        cl-client admin user update 2 -p read:jobs -p write:jobs
    """
    # Validate permissions
    if permissions:
        is_valid, invalid_perms = Permissions.validate(permissions)
        if not is_valid:
            common.output_error(
                ctx,
                f"Invalid permissions: {', '.join(invalid_perms)}. Use 'cl-client admin permissions list' to see allowed permissions.",
            )

    async def run():
        session = await common.get_session_manager(ctx)
        try:
            # Build update request with only provided fields
            user_update = UserUpdateRequest(
                password=password,
                is_admin=admin,
                is_active=active,
                permissions=list(permissions) if permissions else None,
            )

            user = await session.auth_client.update_user(
                token=session.get_token(),
                user_id=user_id,
                user_update=user_update,
            )

            # Output SDK User model directly
            common.output_sdk_result(ctx, user)
        except Exception as e:
            common.output_error(ctx, str(e))
        finally:
            await session.close()

    asyncio.run(run())
