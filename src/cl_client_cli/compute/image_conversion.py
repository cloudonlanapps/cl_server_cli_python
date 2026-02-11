import asyncio
from pathlib import Path
import click
from .. import common
from . import get_compute_client, JobProgressTracker

@click.group("image-conversion")
def image_conversion():
    """Image format conversion."""
    pass

@image_conversion.command("convert")
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "-f",
    "output_format",
    required=True,
    type=click.Choice(["png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff"]),
    help="Output format",
)
@click.option("--quality", "-q", type=int, default=85, help="Quality (1-100)")
@click.option("--watch", is_flag=True, help="Watch progress in real-time")
@click.option("--timeout", "-t", default=60.0, help="Timeout in seconds")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Download output to this file",
)
@click.pass_context
def convert(
    ctx: click.Context,
    image: Path,
    output_format: str,
    quality: int,
    watch: bool,
    timeout: float,
    output: Path | None,
):
    """Convert image to different format.

    Examples:
      cl-client image-conversion convert photo.png -f jpg -q 90
      cl-client image-conversion convert image.jpg -f webp --watch
    """

    async def run():
        async with await get_compute_client(ctx) as client:
            try:
                if watch:
                    tracker = JobProgressTracker(
                        ctx,
                        job_id="pending",
                        description=f"Converting {image.name} to {output_format}",
                    )
                    with tracker:
                        job = await client.image_conversion.convert(
                            image=image,
                            output_format=output_format,
                            quality=quality,
                            on_progress=tracker.on_progress,
                            on_complete=tracker.on_complete,
                        )
                        tracker.job_id = job.job_id
                        final_job = await tracker.wait(timeout=timeout)

                    if final_job and final_job.status == "completed":
                        if not common.should_use_json(ctx):
                            common.console.print("[green]✓ Conversion completed[/green]")
                        common.print_job_result(ctx, final_job)
                        if (
                            output
                            and final_job.params
                            and "output_path" in final_job.params
                        ):
                            output_path = final_job.params["output_path"]
                            await client.download_job_file(
                                final_job.job_id, str(output_path), output
                            )
                            if not common.should_use_json(ctx):
                                common.console.print(f"[green]✓ Downloaded to {output}[/green]")
                    elif final_job:
                        common.output_error(ctx, f"Failed: {final_job.error_message}")
                else:
                    if not common.should_use_json(ctx):
                        with common.console.status("[bold green]Converting..."):
                            job = await client.image_conversion.convert(
                                image=image,
                                output_format=output_format,
                                quality=quality,
                                wait=True,
                                timeout=timeout,
                            )
                    else:
                        job = await client.image_conversion.convert(
                            image=image,
                            output_format=output_format,
                            quality=quality,
                            wait=True,
                            timeout=timeout,
                        )

                    if job.status == "completed":
                        if not common.should_use_json(ctx):
                            common.console.print("[green]✓ Completed[/green]")
                        common.print_job_result(ctx, job)
                        if output and job.params and "output_path" in job.params:
                            output_path = job.params["output_path"]
                            await client.download_job_file(
                                job.job_id, str(output_path), output
                            )
                            if not common.should_use_json(ctx):
                                common.console.print(f"[green]✓ Downloaded to {output}[/green]")
                    else:
                        common.output_error(ctx, f"Failed: {job.error_message}")
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
