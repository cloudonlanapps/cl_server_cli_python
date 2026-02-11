import asyncio
from pathlib import Path
import click
from .. import common
from . import get_store_manager

@click.command("create")
@click.option("--label", help="Entity label/name")
@click.option("--description", help="Entity description")
@click.option("--collection", is_flag=True, help="Create as collection (folder)")
@click.option("--parent-id", type=int, help="Parent collection ID")
@click.option(
    "--file", type=click.Path(exists=True, path_type=Path), help="Media file to upload"
)
@click.pass_context
def create_entity(
    ctx: click.Context,
    label: str | None,
    description: str | None,
    collection: bool,
    parent_id: int | None,
    file: Path | None,
):
    """Create a new entity (collection or media with file).

    DEPRECATED: Use 'upload' command instead for file uploads.

    Examples:
        cl-client store create --label "My Photos" --collection
        cl-client store create --label "Beach Sunset" --file sunset.jpg
    """

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                result = await manager.create_entity(
                    label=label,
                    description=description,
                    is_collection=collection,
                    parent_id=parent_id,
                    image_path=file,
                )

                if result.is_error or result.data is None:
                    common.output_error(
                        ctx, str(result.error) if result.is_error else "No data returned"
                    )

                # Output SDK EntityResult model directly
                common.output_sdk_result(ctx, result.data)
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
