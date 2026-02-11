import asyncio
import click
from ... import common

@click.command("get")
@click.argument("user_id", type=int)
@click.pass_context
def get_user(ctx: click.Context, user_id: int):
    """Get user details by ID (admin only).

    Examples:
        cl-client admin user get 2
    """

    async def run():
        session = await common.get_session_manager(ctx)
        try:
            user = await session.auth_client.get_user(
                token=session.get_token(),
                user_id=user_id,
            )

            # Output SDK User model directly
            common.output_sdk_result(ctx, user)
        except Exception as e:
            common.output_error(ctx, str(e))
        finally:
            await session.close()

    asyncio.run(run())
