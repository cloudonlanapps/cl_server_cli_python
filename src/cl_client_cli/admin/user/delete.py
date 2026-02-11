import asyncio
import click
from ... import common

@click.command("delete")
@click.argument("user_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete_user(ctx: click.Context, user_id: int, yes: bool):
    """Delete user (admin only).

    Examples:
        cl-client admin user delete 2
        cl-client admin user delete 2 --yes  # Skip confirmation
    """

    async def run():
        session = await common.get_session_manager(ctx)
        try:
            # Get user details first for confirmation
            user = await session.auth_client.get_user(
                token=session.get_token(),
                user_id=user_id,
            )

            if not yes:
                click.confirm(
                    f"Are you sure you want to delete user '{user.username}' (ID: {user_id})?",
                    abort=True,
                    err=True,
                )

            await session.auth_client.delete_user(
                token=session.get_token(),
                user_id=user_id,
            )

            # Output success response for void operation
            success = common.SuccessResponse(
                message=f"User '{user.username}' deleted successfully"
            )
            common.output_sdk_result(ctx, success)
        except click.Abort:
            common.output_error(ctx, "Deletion cancelled")
        except Exception as e:
            common.output_error(ctx, str(e))
        finally:
            await session.close()

    asyncio.run(run())
