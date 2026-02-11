import asyncio
import click
from .. import common
from . import get_store_manager

@click.group("face")
def face():
    """Manage faces in the store."""
    pass

@face.command("delete")
@click.argument("face_id", type=int)
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete_face(ctx: click.Context, face_id: int, yes: bool):
    """Delete a face from the database."""

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                if not yes:
                    click.confirm(
                        f"Are you sure you want to delete face ID: {face_id}?",
                        abort=True,
                    )

                result = await manager.delete_face(face_id)
                common.output_sdk_result(ctx, result)
            except click.Abort:
                common.output_error(ctx, "Deletion cancelled")
            except Exception as e:
                common.output_error(ctx, str(e))
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
