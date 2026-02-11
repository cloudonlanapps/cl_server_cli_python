import asyncio
import click
from .. import common
from . import get_store_manager

@click.command("delete")
@click.argument("entity_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete_entity(ctx: click.Context, entity_id: int, yes: bool):
    """Permanently delete an entity (hard delete).

    Examples:
        cl-client store delete 123
        cl-client store delete 123 --yes  # Skip confirmation
    """

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                # Get entity details first for confirmation
                if not yes:
                    read_result = await manager.read_entity(entity_id=entity_id)
                    if read_result.is_error:
                        common.output_error(ctx, str(read_result.error))

                    if read_result.data is None:
                        common.output_error(ctx, "No data returned")

                    entity = read_result.data
                    entity_label = entity.label if entity.label else "(no label)"
                    click.confirm(
                        f"Are you sure you want to permanently delete entity '{entity_label}' (ID: {entity_id})?",
                        abort=True,
                    )

                result = await manager.delete_entity(entity_id=entity_id)

                if result.is_error:
                    common.output_error(ctx, str(result.error))

                # Output success response for void operation
                success = common.SuccessResponse(message=f"Deleted entity [ID: {entity_id}]")
                common.output_sdk_result(ctx, success)
            except click.Abort:
                common.output_error(ctx, "Deletion cancelled")
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
