import asyncio
from pathlib import Path
import click
from .. import common
from . import get_store_manager

@click.command("intelligence")
@click.argument("entity_id", type=int)
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Save output to file")
@click.pass_context
def get_intelligence(ctx: click.Context, entity_id: int, output: Path | None):
    """Get intelligence data for an entity."""

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                result = await manager.get_entity_intelligence(entity_id=entity_id)

                if result.is_error or result.data is None:
                    common.output_error(
                        ctx, str(result.error) if result.is_error else "No intelligence data found"
                    )

                common.output_sdk_result(ctx, result.data)

                if output:
                    with open(output, "w") as f:
                        f.write(result.data.model_dump_json(indent=2))
                    if not common.should_use_json(ctx):
                        click.echo(f"Saved to {output}", err=True)
            except Exception as e:
                common.output_error(ctx, str(e))
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
