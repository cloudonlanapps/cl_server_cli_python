import asyncio
from pathlib import Path
import click
from .. import common
from . import get_compute_client, JobProgressTracker

@click.group("dino-embedding")
def dino_embedding():
    """DINO image embedding operations."""
    pass

@dino_embedding.command("embed")
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option("--watch", "-w", is_flag=True, help="Watch progress in real-time")
@click.option("--timeout", "-t", default=60.0, help="Timeout in seconds")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Download output to this file",
)
@click.pass_context
def embed(
    ctx: click.Context, image: Path, watch: bool, timeout: float, output: Path | None
):
    """Generate DINO embedding for an image.

    Returns 384-dimensional embedding vector.
    """

    async def run():
        async with await get_compute_client(ctx) as client:
            try:
                if watch:
                    # Real-time progress with MQTT
                    tracker = JobProgressTracker(
                        ctx, job_id="pending", description=f"DINO embedding: {image.name}"
                    )
                    with tracker:
                        job = await client.dino_embedding.embed_image(
                            image=image,
                            on_progress=tracker.on_progress,
                            on_complete=tracker.on_complete,
                        )
                        tracker.job_id = job.job_id
                        final_job = await tracker.wait(timeout=timeout)

                    if final_job and final_job.status == "completed":
                        if not common.should_use_json(ctx):
                            common.console.print("[green]✓ Embedding generated[/green]")
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
                        with common.console.status("[bold green]Processing..."):
                            job = await client.dino_embedding.embed_image(
                                image=image,
                                wait=True,
                                timeout=timeout,
                            )
                    else:
                        job = await client.dino_embedding.embed_image(
                            image=image,
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
