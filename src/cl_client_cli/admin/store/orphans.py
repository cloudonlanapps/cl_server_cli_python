import asyncio
import click
from ... import common
from ...store import get_store_manager

@click.command("clear-orphans")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def store_clear_orphans(ctx: click.Context, yes: bool):
    """Clear orphaned resources (admin only).

    Removes orphaned files, faces, vectors, and MQTT messages.

    Examples:
        cl-client admin store clear-orphans
        cl-client admin store clear-orphans --yes  # Skip confirmation
    """

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                # Get audit report first for confirmation
                if not yes:
                    audit_result = await manager.get_audit_report()
                    if audit_result.is_error or audit_result.data is None:
                        common.output_error(
                            ctx,
                            str(audit_result.error)
                            if audit_result.is_error
                            else "No data returned",
                        )
                    
                    # Confirm if anything to clear
                    report = audit_result.data
                    total_orphans = (
                        len(report.orphaned_files) +
                        len(report.orphaned_faces) +
                        len(report.orphaned_vectors) +
                        len(report.orphaned_mqtt)
                    )
                    
                    if total_orphans == 0:
                        click.echo("No orphaned resources found.", err=True)
                        return

                    click.confirm(
                        f"Found {total_orphans} orphaned resources. Clear them?",
                        abort=True,
                    )

                result = await manager.clear_orphans()

                if result.is_error or result.data is None:
                    common.output_error(
                        ctx, str(result.error) if result.is_error else "No data returned"
                    )

                # Output SDK CleanupReport model directly
                common.output_sdk_result(ctx, result.data)
            except click.Abort:
                common.output_error(ctx, "Cleanup cancelled")
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
