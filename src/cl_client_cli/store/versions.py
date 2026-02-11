import asyncio
import json
from pathlib import Path
import click
from .. import common
from . import get_store_manager

@click.command("versions")
@click.argument("entity_id", type=int)
@click.option(
    "--output", "-o", type=click.Path(path_type=Path), help="Save versions to JSON file"
)
@click.pass_context
def get_versions(ctx: click.Context, entity_id: int, output: Path | None):
    """Get version history for an entity.

    Examples:
        cl-client store versions 123
        cl-client store versions 123 --output versions.json
    """

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                result = await manager.get_versions(entity_id)

                if result.is_error or result.data is None:
                    common.output_error(
                        ctx, str(result.error) if result.is_error else "No data returned"
                    )

                # Output SDK list of EntityVersion models as JSON array
                click.echo(
                    json.dumps(
                        [v.model_dump(mode="json", exclude_none=True) for v in result.data],
                        indent=2,
                    )
                )

                # Save to file if requested
                if output:
                    with open(output, "w") as f:
                        json.dump(
                            [v.model_dump() for v in result.data], f, indent=2, default=str
                        )
                    if not common.should_use_json(ctx):
                        click.echo(f"Saved to {output}", err=True)
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
