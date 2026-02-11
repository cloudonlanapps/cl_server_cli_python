import click
from .. import common
from .utils import get_compute_client
from .job_tracker import JobProgressTracker

@click.group(cls=common.JSONGroup)
@click.pass_context
def compute(ctx: click.Context):
    """Compute operations (media processing plugins)."""
    # Load cached config before any compute command runs
    context = common.load_cached_config_or_exit(ctx)

    # Apply JSON override from root CLI if present
    if ctx.parent and ctx.parent.obj and 'json_override' in ctx.parent.obj:
        if ctx.parent.obj['json_override']:
            context.config.output_json = True

    ctx.obj = context

__all__ = ["compute", "get_compute_client", "JobProgressTracker"]

# Import subcommands to register them
from .clip_embedding import clip_embedding
from .media_thumbnail import media_thumbnail
from .hash import hash_group
from .exif import exif
from .image_conversion import image_conversion
from .dino_embedding import dino_embedding
from .face_detection import face_detection
from .face_embedding import face_embedding
from .hls_streaming import hls_streaming

compute.add_command(clip_embedding, name="clip-embedding")
compute.add_command(media_thumbnail, name="media-thumbnail")
compute.add_command(hash_group, name="hash")
compute.add_command(exif)
compute.add_command(image_conversion, name="image-conversion")
compute.add_command(dino_embedding, name="dino-embedding")
compute.add_command(face_detection, name="face-detection")
compute.add_command(face_embedding, name="face-embedding")
compute.add_command(hls_streaming, name="hls-streaming")
