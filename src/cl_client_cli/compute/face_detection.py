import asyncio
from pathlib import Path
import click
from .. import common
from . import get_compute_client, JobProgressTracker

@click.group("face-detection")
def face_detection():
    """Face detection operations."""
    pass

@face_detection.command("detect")
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option("--watch", "-w", is_flag=True, help="Watch progress in real-time")
@click.option("--timeout", "-t", default=60.0, help="Timeout in seconds")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Download face images to this directory",
)
@click.pass_context
def detect_faces(
    ctx: click.Context, image: Path, watch: bool, timeout: float, output: Path | None
):
    """Detect faces in an image.

    Returns bounding boxes, confidence scores, landmarks, and cropped face images.

    Examples:
        cl-client compute face-detection detect photo.jpg
        cl-client compute face-detection detect photo.jpg --output faces/
    """

    async def run():
        async with await get_compute_client(ctx) as client:
            try:
                if watch:
                    tracker = JobProgressTracker(
                        ctx, job_id="pending", description=f"Face detection: {image.name}"
                    )
                    with tracker:
                        job = await client.face_detection.detect(
                            image=image,
                            on_progress=tracker.on_progress,
                            on_complete=tracker.on_complete,
                        )
                        tracker.job_id = job.job_id
                        final_job = await tracker.wait(timeout=timeout)

                    if final_job and final_job.status == "completed":
                        if not common.should_use_json(ctx):
                            common.console.print("[green]✓ Face detection completed[/green]")
                        common.print_job_result(ctx, final_job)

                        # Download face images if output specified
                        if output and final_job.task_output and "faces" in final_job.task_output:
                            output.mkdir(parents=True, exist_ok=True)
                            faces_raw = final_job.task_output["faces"]
                            if isinstance(faces_raw, list):
                                from pydantic import TypeAdapter
                                from cl_client import FaceResponse
                                faces = TypeAdapter(list[FaceResponse]).validate_python(faces_raw)
                                for i, face in enumerate(faces):
                                    face_file = output / f"face_{i}.png"
                                    await client.download_job_file(
                                        final_job.job_id, face.file_path, face_file
                                    )
                                if not common.should_use_json(ctx):
                                    common.console.print(
                                        f"[green]✓ Downloaded {len(faces)} face(s) to {output}[/green]"
                                    )

                    elif final_job:
                        common.output_error(ctx, f"Failed: {final_job.error_message}")
                else:
                    if not common.should_use_json(ctx):
                        with common.console.status("[bold green]Processing..."):
                            job = await client.face_detection.detect(
                                image=image, wait=True, timeout=timeout
                            )
                    else:
                        job = await client.face_detection.detect(
                            image=image, wait=True, timeout=timeout
                        )

                    if job.status == "completed":
                        if not common.should_use_json(ctx):
                            common.console.print("[green]✓ Completed[/green]")
                        common.print_job_result(ctx, job)

                        if output and job.task_output and "faces" in job.task_output:
                            output.mkdir(parents=True, exist_ok=True)
                            faces_raw = job.task_output["faces"]
                            if isinstance(faces_raw, list):
                                from pydantic import TypeAdapter
                                from cl_client import FaceResponse
                                faces = TypeAdapter(list[FaceResponse]).validate_python(faces_raw)
                                for i, face in enumerate(faces):
                                    face_file = output / f"face_{i}.png"
                                    await client.download_job_file(
                                        job.job_id, face.file_path, face_file
                                    )
                                if not common.should_use_json(ctx):
                                    common.console.print(
                                        f"[green]✓ Downloaded {len(faces)} face(s) to {output}[/green]"
                                    )
                    else:
                        common.output_error(ctx, f"Failed: {job.error_message}")

            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
