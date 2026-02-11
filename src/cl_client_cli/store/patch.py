import asyncio
import click
from .. import common
from . import get_store_manager

@click.command("patch")
@click.argument("entity_id", type=int)
@click.option("--label", help="Update label")
@click.option("--description", help="Update description")
@click.option("--parent-id", type=int, help="Update parent ID")
@click.option(
    "--delete", "soft_delete", is_flag=True, help="Soft delete (set is_deleted=true)"
)
@click.option("--restore", is_flag=True, help="Restore (set is_deleted=false)")
@click.pass_context
def patch_entity(
    ctx: click.Context,
    entity_id: int,
    label: str | None,
    description: str | None,
    parent_id: int | None,
    soft_delete: bool,
    restore: bool,
):
    """Partial update of an entity (only update specified fields).

    Examples:
        cl-client store patch 123 --label "New Label"
        cl-client store patch 123 --description "Updated description"
        cl-client store patch 123 --delete
        cl-client store patch 123 --restore
    """
    if soft_delete and restore:
        common.output_error(ctx, "Cannot use both --delete and --restore")

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                is_deleted = None
                if soft_delete:
                    is_deleted = True
                elif restore:
                    is_deleted = False

                result = await manager.patch_entity(
                    entity_id=entity_id,
                    label=label,
                    description=description,
                    parent_id=parent_id,
                    is_deleted=is_deleted,
                )

                if result.is_error:
                    common.output_error(ctx, str(result.error))

                # Output success response for void operation
                action = "Deleted" if soft_delete else "Restored" if restore else "Updated"
                success = common.SuccessResponse(message=f"{action} entity [ID: {entity_id}]")
                common.output_sdk_result(ctx, success)
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
