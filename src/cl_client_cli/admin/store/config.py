import asyncio
import click
from ... import common
from ...store import get_store_manager

@click.command("config")
@click.pass_context
def store_get_config(ctx: click.Context):
    """Get store configuration (admin only).

    Examples:
        cl-client admin store config
    """

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                result = await manager.get_pref()

                if result.is_error or result.data is None:
                    common.output_error(
                        ctx, str(result.error) if result.is_error else "No data returned"
                    )

                # Output SDK Config model directly
                common.output_sdk_result(ctx, result.data)
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
