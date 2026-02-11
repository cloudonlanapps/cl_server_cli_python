import asyncio
import json
from pathlib import Path
import click
from .. import common
from . import get_store_manager

@click.command("list")
@click.option("--page", default=1, type=int, help="Page number (1-indexed)")
@click.option("--page-size", default=20, type=int, help="Items per page (max 100)")
@click.option("--search", help="Search query for label/description")
@click.option(
    "--output", "-o", type=click.Path(path_type=Path), help="Save results to JSON file"
)
@click.pass_context
def list_entities(
    ctx: click.Context,
    page: int,
    page_size: int,
    search: str | None,
    output: Path | None,
):
    """List entities with pagination and search.

    Examples:
        cl-client store list --page 1 --page-size 20
        cl-client store list --search "vacation"
        cl-client store list --output entities.json
    """

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                result = await manager.list_entities(
                    page=page,
                    page_size=page_size,
                    search_query=search,
                )

                if result.is_error or result.data is None:
                    common.output_error(
                        ctx, str(result.error) if result.is_error else "No data returned"
                    )

                # Output SDK EntityListResult model directly
                common.output_sdk_result(ctx, result.data)

                # Save to file if requested (works in both JSON and human mode)
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
