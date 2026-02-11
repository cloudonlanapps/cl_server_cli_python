import asyncio
import json
import click
from ... import common

@click.command("list")
@click.option("--skip", default=0, help="Number of users to skip")
@click.option("--limit", default=100, help="Maximum number of users to return")
@click.pass_context
def list_users(ctx: click.Context, skip: int, limit: int):
    """List all users (admin only).

    Examples:
        cl-client admin user list
        cl-client admin user list --skip 10 --limit 20
    """

    async def run():
        session = await common.get_session_manager(ctx)
        try:
            users = await session.auth_client.list_users(
                token=session.get_token(),
                skip=skip,
                limit=limit,
            )

            # For lists, output as JSON array directly
            click.echo(
                json.dumps(
                    [u.model_dump(mode="json", exclude_none=True) for u in users],
                    indent=2,
                )
            )
        except Exception as e:
            common.output_error(ctx, str(e))
        finally:
            await session.close()

    asyncio.run(run())
