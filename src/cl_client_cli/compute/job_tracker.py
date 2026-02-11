import asyncio
import click
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from cl_client.models import JobResponse
from ..common.context import CLIContext
from ..common.helper import output_error, console

class JobProgressTracker:
    """Track job progress with optional display.

    When JSON mode is active, suppresses all stdout/stderr output.
    MQTT callbacks are still used internally regardless of JSON mode.
    """

    def __init__(self, ctx: click.Context, job_id: str, description: str):
        self.ctx = ctx
        self.job_id = job_id
        self.description = description
        self.completed = asyncio.Event()
        self.final_job: JobResponse | None = None
        
        # Access context via Pydantic model
        context: CLIContext = ctx.obj
        self.use_json = context.output_json

        if not self.use_json:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            )
            self.task_id = None  # Will be set to TaskID when progress starts
        else:
            # JSON mode: no visual progress, but MQTT callbacks still run
            self.progress = None
            self.task_id = None

    def __enter__(self):
        """Start progress display (only if not in JSON mode)."""
        if self.progress:
            self.progress.start()
            self.task_id = self.progress.add_task(self.description, total=100)
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Stop progress display (only if not in JSON mode)."""
        if self.progress:
            self.progress.stop()

    def on_progress(self, job: JobResponse):
        """Update progress bar (only if not in JSON mode)."""
        if self.progress and self.task_id is not None:
            self.progress.update(
                self.task_id,
                completed=job.progress,
                description=f"{self.description} [{job.status}]",
            )

    def on_complete(self, job: JobResponse):
        """Handle job completion."""
        self.final_job = job
        if self.progress and self.task_id is not None:
            self.progress.update(
                self.task_id,
                completed=100,
                description=f"{self.description} [{job.status}]",
            )
        self.completed.set()

    async def wait(self, timeout: float = 60.0) -> JobResponse:
        """Wait for job completion."""
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            if self.completed.is_set():
                if self.final_job:
                    return self.final_job
                break
            await asyncio.sleep(0.5)

        output_error(
            ctx=self.ctx, error_message=f"Job {self.job_id} timed out after {timeout}s"
        )
