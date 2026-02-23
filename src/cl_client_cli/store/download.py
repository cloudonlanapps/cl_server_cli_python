import asyncio
import json
import sys
from pathlib import Path

import click
from .. import common
from cl_client.store_models import Entity
from . import get_store_manager

def format_face_json(entity: Entity, faces, output_path: Path):
    """Format face data into sample1.jpg.json format and save."""
    face_list = []
    if faces and getattr(faces, "data", None):
        for f in faces.data:
            landmarks = {
                "leftEye": list(f.landmarks.left_eye),
                "rightEye": list(f.landmarks.right_eye),
                "noseTip": list(f.landmarks.nose_tip),
                "mouthLeft": list(f.landmarks.mouth_left),
                "mouthRight": list(f.landmarks.mouth_right),
            }
            face_data = {
                "id": f.id,
                "bbox": {
                    "x1": f.bbox.x1,
                    "y1": f.bbox.y1,
                    "x2": f.bbox.x2,
                    "y2": f.bbox.y2,
                },
                "confidence": f.confidence,
                "landmarks": landmarks,
                "knownPersonId": f.known_person_id
            }
            face_list.append(face_data)
            
    width = 0
    height = 0
    if hasattr(entity, 'width') and entity.width: width = entity.width
    if hasattr(entity, 'height') and entity.height: height = entity.height

    output_data = {
        "name": entity.label or f"Image {entity.id}",
        "width": width,
        "height": height,
        "faces": face_list
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)


@click.command("download")
@click.option("--id", "entity_id", type=int, help="Download a specific image by ID")
@click.option("--page", default=1, type=int, help="Page number to fetch")
@click.option("--per-page", default=20, type=int, help="Results per page")
@click.option("--out-dir", default="downloads", type=str, help="Output directory")
@click.pass_context
def download_media(ctx: click.Context, entity_id: int | None, page: int, per_page: int, out_dir: str):
    """Download images and their face JSON to a local directory."""

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"Saving downloads to directory: {out_path.absolute()}", err=True)

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                items = []
                pagination = None
                
                if entity_id is not None:
                    click.echo(f"Fetching specific image ID {entity_id}...", err=True)
                    result = await manager.read_entity(entity_id=entity_id)
                    if result.is_error or not result.data:
                        common.output_error(ctx, str(result.error) if result.is_error else f"Failed to find entity {entity_id}")
                        return
                    items = [result.data]
                    click.echo(f"Found 1 item.", err=True)
                else:
                    click.echo(f"Fetching page {page} (size: {per_page})...", err=True)
                    result = await manager.list_entities(
                        page=page, 
                        page_size=per_page, 
                        type_="image" # Only images
                    )
                    
                    if result.is_error or not result.data:
                        common.output_error(ctx, str(result.error) if result.is_error else "Failed to list entities")
                        return

                    pagination = getattr(result.data, 'pagination', None)
                    if pagination:
                        click.echo(f"Page {pagination.page} of {pagination.total_pages} (Total items in database: {pagination.total_items})", err=True)
                    else:
                        click.echo(f"Found {len(result.data.items)} items in the current request.", err=True)
                    
                    items = result.data.items
                    
                if not items:
                    click.echo("No images found.", err=True)
                    return
                    
                for entity in items:
                    ext = "jpg"
                    if entity.mime_type:
                        ext = entity.mime_type.split("/")[-1]
                        if ext == "jpeg": ext = "jpg"
                    
                    filename = f"{entity.id}.{ext}"
                    filepath = out_path / filename
                    jsonpath = out_path / f"{filename}.json"
                    
                    click.echo(f"Downloading {filename}...", err=True)
                    media_res = await manager.download_media(entity.id)
                    if media_res.is_success and media_res.data:
                        with open(filepath, "wb") as f:
                            f.write(media_res.data)
                    else:
                        click.echo(f"  Failed to download media: {media_res.error}", err=True)
                        continue
                        
                    click.echo(f"Fetching faces for {entity.id}...", err=True)
                    faces_res = await manager.get_entity_faces(entity_id=entity.id)
                    
                    format_face_json(entity, faces_res if faces_res.is_success else None, jsonpath)
                    click.echo(f"  Saved {filename} and {filename}.json", err=True)
                    
                if entity_id is None:
                    if pagination and pagination.page < pagination.total_pages:
                        click.echo(f"\nMore pages available! Run with --page {page + 1}", err=True)
                    else:
                        click.echo(f"\nNo more pages.", err=True)
                
            except Exception as e:
                common.output_error(ctx, f"Error: {e}")
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
