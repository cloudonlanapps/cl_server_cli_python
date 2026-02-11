import asyncio
import json
from pathlib import Path
import click
from .. import common
from . import get_store_manager

@click.command("get")
@click.argument("entity_id", type=int)
@click.option("--version", type=int, help="Specific version to retrieve")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Save entity data to JSON file",
)
@click.pass_context
def get_entity(
    ctx: click.Context, entity_id: int, version: int | None, output: Path | None
):
    """Get entity by ID (optionally specific version).

    Examples:
        cl-client store get 123
        cl-client store get 123 --version 2
        cl-client store get 123 --output entity.json
    """

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                result = await manager.read_entity(entity_id=entity_id, version=version)

                if result.is_error or result.data is None:
                    common.output_error(
                        ctx, str(result.error) if result.is_error else "No data returned"
                    )

                # Output SDK EntityResult model directly
                common.output_sdk_result(ctx, result.data)

                # Save to file if requested
                if output:
                    with open(output, "w") as f:
                        json.dump(result.data.model_dump(), f, indent=2, default=str)
                    if not common.should_use_json(ctx):
                        click.echo(f"Saved to {output}", err=True)
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
