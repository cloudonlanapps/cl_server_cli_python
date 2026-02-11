import asyncio
import click
from ... import common

@click.command("capabilities")
@click.pass_context
def capabilities(ctx: click.Context):
    """Show current worker capabilities and availability.

    Examples:
        cl-client admin compute capabilities
    """

    async def run():
        session = await common.get_session_manager(ctx)
        try:
            client = session.create_compute_client()
            caps = await client.get_capabilities()
            common.output_sdk_result(ctx, caps)
        except Exception as e:
            common.output_error(ctx, str(e))
        finally:
            context: common.CLIContext = ctx.obj
            if context.session:
                await context.session.close()

    asyncio.run(run())
