import asyncio
from pathlib import Path
import click
from .. import common
from . import get_compute_client, JobProgressTracker

@click.group("exif")
def exif():
    """EXIF metadata extraction."""
    pass

@exif.command("extract")
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option("--watch", is_flag=True, help="Watch progress in real-time")
@click.option("--timeout", "-t", default=30.0, help="Timeout in seconds")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Download EXIF output to this file",
)
@click.pass_context
def extract(
    ctx: click.Context, image: Path, watch: bool, timeout: float, output: Path | None
):
    """Extract EXIF metadata from an image."""

    async def run():
        async with await get_compute_client(ctx) as client:
            try:
                if watch:
                    tracker = JobProgressTracker(
                        ctx, job_id="pending", description=f"EXIF extraction: {image.name}"
                    )
                    with tracker:
                        job = await client.exif.extract(
                            image=image,
                            on_progress=tracker.on_progress,
                            on_complete=tracker.on_complete,
                        )
                        tracker.job_id = job.job_id
                        final_job = await tracker.wait(timeout=timeout)

                    if final_job and final_job.status == "completed":
                        if not common.should_use_json(ctx):
                            common.console.print("[green]✓ EXIF extracted[/green]")
                        common.print_job_result(ctx, final_job)

                        # Download if output specified
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
                        with common.console.status("[bold green]Extracting EXIF..."):
                            job = await client.exif.extract(
                                image=image,
                                wait=True,
                                timeout=timeout,
                            )
                    else:
                        job = await client.exif.extract(
                            image=image,
                            wait=True,
                            timeout=timeout,
                        )

                    if job.status == "completed":
                        if not common.should_use_json(ctx):
                            common.console.print("[green]✓ Completed[/green]")
                        common.print_job_result(ctx, job)

                        # Download if output specified
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
