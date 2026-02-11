import asyncio
from pathlib import Path
import click
from .. import common
from . import get_store_manager

@click.command("update")
@click.argument("entity_id", type=int)
@click.option("--label", required=True, help="New label")
@click.option("--description", help="New description")
@click.option("--collection", is_flag=True, help="Set as collection")
@click.option("--parent-id", type=int, help="New parent collection ID")
@click.option(
    "--file", type=click.Path(exists=True, path_type=Path), help="New media file"
)
@click.pass_context
def update_entity(
    ctx: click.Context,
    entity_id: int,
    label: str,
    description: str | None,
    collection: bool,
    parent_id: int | None,
    file: Path | None,
):
    """Full update of an entity (requires label).

    Examples:
        cl-client store update 123 --label "Updated Label"
        cl-client store update 123 --label "New Title" --description "Updated desc"
        cl-client store update 123 --label "Photo" --file new_photo.jpg
    """

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                result = await manager.update_entity(
                    entity_id=entity_id,
                    label=label,
                    description=description,
                    is_collection=collection,
                    parent_id=parent_id,
                    image_path=file,
                )

                if result.is_error:
                    common.output_error(ctx, str(result.error))

                # Output success response for void operation
                success = common.SuccessResponse(message=f"Updated entity [ID: {entity_id}]")
                common.output_sdk_result(ctx, success)
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
