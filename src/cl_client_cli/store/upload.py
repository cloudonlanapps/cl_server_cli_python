import asyncio
from pathlib import Path
import click
from .. import common
from . import get_store_manager

@click.command("upload")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--label", help="Entity label/name (for single file)")
@click.option("--description", help="Entity description")
@click.option("--parent-id", type=int, help="Parent collection ID")
@click.option("--recursive", "-r", is_flag=True, help="Recursively upload all images in directory")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation for batch uploads")
@click.pass_context
def upload_entity(
    ctx: click.Context,
    path: Path,
    label: str | None,
    description: str | None,
    parent_id: int | None,
    recursive: bool,
    yes: bool,
):
    """Upload media file or directory to store.

    Examples:
        cl-client store upload photo.jpg --label "Beach Sunset"
        cl-client store upload photo.jpg --label "Vacation" --description "Summer 2024" --parent-id 5
        cl-client store upload photos/ --recursive --parent-id 5
        cl-client store upload photos/ -r --yes  # Skip confirmation
    """

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                # Check if path is directory
                if path.is_dir():
                    if recursive:
                        # Find all images in directory
                        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic'}
                        image_files = [
                            f for f in path.rglob('*')
                            if f.is_file() and f.suffix.lower() in image_extensions
                        ]

                        if not image_files:
                            common.output_error(ctx, f"No image files found in {path}")

                        # Confirm batch upload
                        if not yes:
                            click.confirm(
                                f"Found {len(image_files)} image(s) to upload. Continue?",
                                abort=True,
                            )

                        # Upload each file
                        success_count = 0
                        output_json = ctx.obj.output_json

                        for img_file in image_files:
                            try:
                                # Use relative path as label if not provided
                                file_label = str(img_file.relative_to(path))
                                result = await manager.create_entity(
                                    label=file_label,
                                    description=description,
                                    is_collection=False,
                                    parent_id=parent_id,
                                    image_path=img_file,
                                )

                                if not result.is_error:
                                    success_count += 1
                                    if not output_json:
                                        click.echo(f"✓ Uploaded: {file_label}", err=True)
                                else:
                                    if not output_json:
                                        click.echo(f"✗ Failed: {file_label} - {result.error}", err=True)

                            except Exception as e:
                                if not output_json:
                                    click.echo(f"✗ Error: {img_file.name} - {e}", err=True)

                        # Output summary
                        success = common.SuccessResponse(
                            message=f"Uploaded {success_count}/{len(image_files)} images"
                        )
                        common.output_sdk_result(ctx, success)

                    else:
                        common.output_error(ctx, f"{path} is a directory. Use --recursive to upload all images.")

                else:
                    # Single file upload
                    result = await manager.create_entity(
                        label=label or path.name,
                        description=description,
                        is_collection=False,
                        parent_id=parent_id,
                        image_path=path,
                    )

                    if result.is_error or result.data is None:
                        common.output_error(
                            ctx, str(result.error) if result.is_error else "No data returned"
                        )

                    # Output SDK EntityResult model directly
                    common.output_sdk_result(ctx, result.data)

            except click.Abort:
                common.output_error(ctx, "Upload cancelled")
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
