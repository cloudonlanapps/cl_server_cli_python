import asyncio
import click
from cl_client import UserCreateRequest
from ... import common
from .permissions import Permissions

@click.command("create")
@click.argument("username", type=str)
@click.argument("password", type=str)
@click.option("--admin", is_flag=True, default=False, help="Grant admin privileges")
@click.option(
    "--permissions",
    "-p",
    multiple=True,
    help="Permissions to grant (can specify multiple times)",
)
@click.pass_context
def create_user(
    ctx: click.Context,
    username: str,
    password: str,
    admin: bool,
    permissions: tuple[str, ...],
):
    """Create a new user (admin only).

    Examples:
        cl-client admin user create newuser pass123
        cl-client admin user create john doe123 --admin
        cl-client admin user create jane doe456 -p read:jobs -p write:jobs
    """
    # Validate permissions
    if permissions:
        is_valid: bool
        invalid_perms: list[str]
        is_valid, invalid_perms = Permissions.validate(permissions)
        if not is_valid:
            common.output_error(
                ctx,
                f"Invalid permissions: {', '.join(invalid_perms)}. Use 'cl-client admin permissions list' to see allowed permissions.",
            )

    async def run():
        session = await common.get_session_manager(ctx)
        try:
            user_create = UserCreateRequest(
                username=username,
                password=password,
                is_admin=admin,
                is_active=True,
                permissions=list(permissions) if permissions else [],
            )

            user = await session.auth_client.create_user(
                token=session.get_token(),
                user_create=user_create,
            )

            # Output the SDK User model directly
            common.output_sdk_result(ctx, user)
        except Exception as e:
            common.output_error(ctx, str(e))
        finally:
            await session.close()

    asyncio.run(run())
