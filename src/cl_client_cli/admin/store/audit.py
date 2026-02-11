import asyncio
import click
from ... import common
from ...store import get_store_manager

@click.command("audit-report")
@click.pass_context
def store_audit_report(ctx: click.Context):
    """Generate audit report of orphaned resources (admin only).

    Reports orphaned files, faces, vectors, and MQTT messages.

    Examples:
        cl-client admin store audit-report
        cl-client admin store audit-report --json
    """

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                result = await manager.get_audit_report()

                if result.is_error or result.data is None:
                    common.output_error(
                        ctx, str(result.error) if result.is_error else "No data returned"
                    )

                # Output SDK AuditReport model directly
                common.output_sdk_result(ctx, result.data)
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
