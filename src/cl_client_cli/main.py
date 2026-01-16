"""CL Client CLI - Main command-line interface."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.table import Table

from cl_client import ComputeClient, SessionManager, ServerConfig, StoreManager
from cl_client.models import JobResponse

console = Console()


class JobProgressTracker:
    """Track job progress with Rich progress bar."""

    def __init__(self, job_id: str, description: str):
        self.job_id = job_id
        self.description = description
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        )
        self.task_id = None
        self.completed = asyncio.Event()
        self.final_job: Optional[JobResponse] = None

    def __enter__(self):
        self.progress.start()
        self.task_id = self.progress.add_task(self.description, total=100)
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.progress.stop()

    def on_progress(self, job: JobResponse):
        """Update progress bar."""
        if self.task_id is not None:
            self.progress.update(
                self.task_id,
                completed=job.progress,
                description=f"{self.description} [{job.status}]",
            )

    def on_complete(self, job: JobResponse):
        """Handle job completion."""
        self.final_job = job
        if self.task_id is not None:
            self.progress.update(
                self.task_id,
                completed=100,
                description=f"{self.description} [{job.status}]",
            )
        self.completed.set()

    async def wait(self, timeout: float = 60.0):
        """Wait for job completion."""
        try:
            await asyncio.wait_for(self.completed.wait(), timeout=timeout)
            return self.final_job
        except asyncio.TimeoutError:
            console.print(f"[red]Job {self.job_id} timed out after {timeout}s[/red]")
            return None


def print_job_result(job: JobResponse):
    """Print job result in a nice table."""
    table = Table(title=f"Job {job.job_id}")
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    table.add_row("Job ID", job.job_id)
    table.add_row("Task Type", job.task_type)
    table.add_row("Status", job.status)
    table.add_row("Progress", f"{job.progress}%")

    if job.task_output:
        table.add_row("Output", str(job.task_output))

    if job.error_message:
        table.add_row("Error", job.error_message)

    console.print(table)


@click.group()
@click.version_option()
@click.option(
    "--username",
    envvar="CL_USERNAME",
    help="Username for authentication",
)
@click.option(
    "--password",
    envvar="CL_PASSWORD",
    help="Password for authentication",
)
@click.option(
    "--auth-url",
    envvar="AUTH_URL",
    default="http://localhost:8000",
    help="Auth service URL",
)
@click.option(
    "--compute-url",
    envvar="COMPUTE_URL",
    default="http://localhost:8002",
    help="Compute service URL",
)
@click.option(
    "--store-url",
    envvar="STORE_URL",
    default="http://localhost:8001",
    help="Store service URL",
)
@click.option(
    "--no-auth",
    is_flag=True,
    default=False,
    help="Disable authentication (use no-auth mode)",
)
@click.pass_context
def cli(
    ctx: click.Context,
    username: Optional[str],
    password: Optional[str],
    auth_url: str,
    compute_url: str,
    store_url: str,
    no_auth: bool,
):
    """CL Client CLI - Command-line interface for compute, store, and auth operations.

    Examples:
      # No-auth mode (default if no credentials provided)
      cl-client clip-embedding embed image.jpg --watch

      # With authentication
      cl-client --username user --password pass clip-embedding embed image.jpg

      # Store operations
      cl-client store list --page 1 --page-size 20
      cl-client --username user --password pass store create --label "My Photo" --file photo.jpg

      # Using environment variables
      export CL_USERNAME=user CL_PASSWORD=pass
      cl-client media-thumbnail generate video.mp4 -w 256 -h 256

      # Explicit no-auth mode
      cl-client --no-auth hash compute image.jpg
    """
    # Store config in context for commands to access
    ctx.ensure_object(dict)
    ctx.obj["username"] = username
    ctx.obj["password"] = password
    ctx.obj["auth_url"] = auth_url
    ctx.obj["compute_url"] = compute_url
    ctx.obj["store_url"] = store_url
    ctx.obj["no_auth"] = no_auth
    ctx.obj["server_config"] = ServerConfig(
        auth_url=auth_url,
        compute_url=compute_url,
        store_url=store_url,
    )


async def get_client(ctx: click.Context) -> ComputeClient:
    """Get ComputeClient based on CLI context (auth or no-auth mode).

    Returns:
        ComputeClient instance (caller must close it)
    """
    username = ctx.obj.get("username")
    password = ctx.obj.get("password")
    no_auth = ctx.obj.get("no_auth", False)
    server_config = ctx.obj.get("server_config")

    # If no credentials or --no-auth flag, use no-auth mode
    if no_auth or not (username and password):
        return ComputeClient(
            base_url=server_config.compute_url,
            server_config=server_config,
        )

    # With credentials: create session, login, return client
    session = SessionManager(server_config=server_config)
    try:
        await session.login(username, password)
        # Store session in context for cleanup
        ctx.obj["session"] = session
        return session.create_compute_client()
    except Exception as e:
        await session.close()
        console.print(f"[red]Authentication failed: {e}[/red]")
        sys.exit(1)


async def get_session_manager(ctx: click.Context) -> SessionManager:
    """Get authenticated SessionManager for admin operations.

    Raises:
        SystemExit if authentication fails or no credentials provided
    """
    username = ctx.obj.get("username")
    password = ctx.obj.get("password")
    server_config = ctx.obj.get("server_config")

    if not username or not password:
        console.print(
            "[red]Error: Username and password required for this operation[/red]"
        )
        console.print(
            "Use --username and --password flags or set CL_USERNAME and CL_PASSWORD env vars"
        )
        sys.exit(1)

    session = SessionManager(server_config=server_config)
    try:
        await session.login(username, password)
        return session
    except Exception as e:
        await session.close()
        console.print(f"[red]Authentication failed: {e}[/red]")
        sys.exit(1)


async def get_store_manager(ctx: click.Context):
    """Get StoreManager based on CLI context (auth or guest mode).

    Returns:
        StoreManager instance (caller must close it)
    """
    username = ctx.obj.get("username")
    password = ctx.obj.get("password")
    no_auth = ctx.obj.get("no_auth", False)
    server_config = ctx.obj.get("server_config")

    # If no credentials or --no-auth flag, use guest mode
    if no_auth or not (username and password):
        return StoreManager.guest(base_url=server_config.store_url)

    # With credentials: create session, login, return store manager
    session = SessionManager(server_config=server_config)
    try:
        await session.login(username, password)
        # Store session in context for cleanup
        ctx.obj["session"] = session
        return session.create_store_manager()
    except Exception as e:
        await session.close()
        console.print(f"[red]Authentication failed: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("job_id", type=str)
@click.argument("file_path", type=str)
@click.argument("destination", type=click.Path(path_type=Path), required=False)
@click.pass_context
def download(
    ctx: click.Context, job_id: str, file_path: str, destination: Optional[Path]
):
    """Download output file from a completed job.

    Args:
        job_id: Job ID (UUID)
        file_path: Relative path to file (e.g., "output/embedding.npy")
        destination: Local path to save file (optional, defaults to filename)

    Examples:
        cl-client download abc123 output/clip_embedding.npy embedding.npy
        cl-client download abc123 output/thumbnail.jpg ./result.jpg
    """

    async def run():
        # Default destination to just the filename
        dest_path = destination if destination else Path(Path(file_path).name)

        client = await get_client(ctx)
        try:
            with console.status(f"[bold green]Downloading {file_path}..."):
                await client.download_job_file(job_id, file_path, dest_path)

            console.print(f"[green]✓ Downloaded to {dest_path}[/green]")
            console.print(f"  Job ID: {job_id}")
            console.print(f"  File: {file_path}")
            console.print(f"  Size: {dest_path.stat().st_size} bytes")
        finally:
            await client.close()
            # Close session if exists
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


# User Management Commands


@cli.group()
def user():
    """User management operations (admin only)."""
    pass


@user.command("create")
@click.argument("username", type=str)
@click.argument("password", type=str)
@click.option("--admin", is_flag=True, default=False, help="Grant admin privileges")
@click.option(
    "--permissions",
    "-p",
    multiple=True,
    help="Permissions to grant (can specify multiple times)",
)
@click.pass_context
def user_create(
    ctx: click.Context,
    username: str,
    password: str,
    admin: bool,
    permissions: tuple[str, ...],
):
    """Create a new user (admin only).

    Examples:
        cl-client --username admin --password admin user create newuser pass123
        cl-client user create john doe123 --admin
        cl-client user create jane doe456 -p read:jobs -p write:jobs
    """
    from cl_client import UserCreateRequest

    async def run():
        session = await get_session_manager(ctx)
        try:
            user_create = UserCreateRequest(
                username=username,
                password=password,
                is_admin=admin,
                is_active=True,
                permissions=list(permissions) if permissions else [],
            )

            user = await session.auth_client.create_user(
                token=session.get_token(),
                user_create=user_create,
            )

            console.print("[green]✓ User created successfully[/green]")
            table = Table(title=f"User {user.username}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("ID", str(user.id))
            table.add_row("Username", user.username)
            table.add_row("Admin", "Yes" if user.is_admin else "No")
            table.add_row("Active", "Yes" if user.is_active else "No")
            table.add_row(
                "Permissions",
                ", ".join(user.permissions) if user.permissions else "None",
            )
            console.print(table)
        finally:
            await session.close()

    asyncio.run(run())


@user.command("list")
@click.option("--skip", default=0, help="Number of users to skip")
@click.option("--limit", default=100, help="Maximum number of users to return")
@click.pass_context
def user_list(ctx: click.Context, skip: int, limit: int):
    """List all users (admin only).

    Examples:
        cl-client --username admin --password admin user list
        cl-client user list --skip 10 --limit 20
    """

    async def run():
        session = await get_session_manager(ctx)
        try:
            users = await session.auth_client.list_users(
                token=session.get_token(),
                skip=skip,
                limit=limit,
            )

            if not users:
                console.print("[yellow]No users found[/yellow]")
                return

            table = Table(title=f"Users ({len(users)} found)")
            table.add_column("ID", style="cyan")
            table.add_column("Username", style="green")
            table.add_column("Admin", style="magenta")
            table.add_column("Active", style="blue")
            table.add_column("Permissions", style="yellow")

            for user in users:
                table.add_row(
                    str(user.id),
                    user.username,
                    "✓" if user.is_admin else "",
                    "✓" if user.is_active else "",
                    ", ".join(user.permissions) if user.permissions else "",
                )

            console.print(table)
        finally:
            await session.close()

    asyncio.run(run())


@user.command("get")
@click.argument("user_id", type=int)
@click.pass_context
def user_get(ctx: click.Context, user_id: int):
    """Get user details by ID (admin only).

    Examples:
        cl-client --username admin --password admin user get 2
    """

    async def run():
        session = await get_session_manager(ctx)
        try:
            user = await session.auth_client.get_user(
                token=session.get_token(),
                user_id=user_id,
            )

            table = Table(title=f"User {user.username}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("ID", str(user.id))
            table.add_row("Username", user.username)
            table.add_row("Admin", "Yes" if user.is_admin else "No")
            table.add_row("Active", "Yes" if user.is_active else "No")
            table.add_row("Created", str(user.created_at))
            table.add_row(
                "Permissions",
                ", ".join(user.permissions) if user.permissions else "None",
            )
            console.print(table)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        finally:
            await session.close()

    asyncio.run(run())


@user.command("update")
@click.argument("user_id", type=int)
@click.option("--password", help="New password")
@click.option("--admin/--no-admin", default=None, help="Grant/revoke admin privileges")
@click.option("--active/--inactive", default=None, help="Activate/deactivate user")
@click.option(
    "--permissions",
    "-p",
    multiple=True,
    help="Permissions to grant (replaces existing permissions)",
)
@click.pass_context
def user_update(
    ctx: click.Context,
    user_id: int,
    password: Optional[str],
    admin: Optional[bool],
    active: Optional[bool],
    permissions: tuple[str, ...],
):
    """Update user (admin only).

    Examples:
        cl-client user update 2 --password newpass123
        cl-client user update 2 --admin
        cl-client user update 2 --inactive
        cl-client user update 2 -p read:jobs -p write:jobs -p admin
    """
    from cl_client import UserUpdateRequest

    async def run():
        session = await get_session_manager(ctx)
        try:
            # Build update request with only provided fields
            user_update = UserUpdateRequest(
                password=password,
                is_admin=admin,
                is_active=active,
                permissions=list(permissions) if permissions else None,
            )

            user = await session.auth_client.update_user(
                token=session.get_token(),
                user_id=user_id,
                user_update=user_update,
            )

            console.print("[green]✓ User updated successfully[/green]")
            table = Table(title=f"User {user.username}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("ID", str(user.id))
            table.add_row("Username", user.username)
            table.add_row("Admin", "Yes" if user.is_admin else "No")
            table.add_row("Active", "Yes" if user.is_active else "No")
            table.add_row(
                "Permissions",
                ", ".join(user.permissions) if user.permissions else "None",
            )
            console.print(table)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        finally:
            await session.close()

    asyncio.run(run())


@user.command("delete")
@click.argument("user_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def user_delete(ctx: click.Context, user_id: int, yes: bool):
    """Delete user (admin only).

    Examples:
        cl-client user delete 2
        cl-client user delete 2 --yes  # Skip confirmation
    """

    async def run():
        session = await get_session_manager(ctx)
        try:
            # Get user details first for confirmation
            user = await session.auth_client.get_user(
                token=session.get_token(),
                user_id=user_id,
            )

            if not yes:
                click.confirm(
                    f"Are you sure you want to delete user '{user.username}' (ID: {user_id})?",
                    abort=True,
                )

            await session.auth_client.delete_user(
                token=session.get_token(),
                user_id=user_id,
            )

            console.print(
                f"[green]✓ User '{user.username}' deleted successfully[/green]"
            )
        except click.Abort:
            console.print("[yellow]Deletion cancelled[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        finally:
            await session.close()

    asyncio.run(run())


# Store Commands


@cli.group()
def store():
    """Store operations - manage media entities and collections."""
    pass


@store.command("list")
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
    search: Optional[str],
    output: Optional[Path],
):
    """List entities with pagination and search.

    Examples:
        cl-client store list --page 1 --page-size 20
        cl-client store list --search "vacation"
        cl-client store list --output entities.json
    """
    import json

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            result = await manager.list_entities(
                page=page,
                page_size=page_size,
                search_query=search,
            )

            if result.is_error:
                console.print(f"[red]Error: {result.error}[/red]")
                sys.exit(1)

            # Display results
            if result.data is None:
                console.print("[red]Error: No data returned[/red]")
                sys.exit(1)

            entities = result.data.items
            pagination = result.data.pagination

            console.print(
                f"[bold]Page {pagination.page}/{pagination.total_pages}[/bold] "
                f"(Total: {pagination.total_items} entities)"
            )

            if entities:
                table = Table(title="Entities")
                table.add_column("ID", style="cyan")
                table.add_column("Label", style="green")
                table.add_column("Type", style="magenta")
                table.add_column("Size", style="yellow")
                table.add_column("Updated", style="blue")

                for entity in entities:
                    entity_type = "Collection" if entity.is_collection else "Media"
                    size = f"{entity.file_size} bytes" if entity.file_size else "-"
                    updated = (
                        entity.updated_date_datetime.strftime("%Y-%m-%d %H:%M")
                        if entity.updated_date_datetime
                        else "-"
                    )

                    table.add_row(
                        str(entity.id),
                        entity.label or "(no label)",
                        entity_type,
                        size,
                        updated,
                    )

                console.print(table)
            else:
                console.print("[yellow]No entities found[/yellow]")

            # Save to file if requested
            if output:
                with open(output, "w") as f:
                    json.dump(result.data.model_dump(), f, indent=2, default=str)
                console.print(f"\n[green]✓ Saved to {output}[/green]")
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@store.command("create")
@click.option("--label", help="Entity label/name")
@click.option("--description", help="Entity description")
@click.option("--collection", is_flag=True, help="Create as collection (folder)")
@click.option("--parent-id", type=int, help="Parent collection ID")
@click.option(
    "--file", type=click.Path(exists=True, path_type=Path), help="Media file to upload"
)
@click.pass_context
def create_entity(
    ctx: click.Context,
    label: Optional[str],
    description: Optional[str],
    collection: bool,
    parent_id: Optional[int],
    file: Optional[Path],
):
    """Create a new entity (collection or media with file).

    Examples:
        cl-client store create --label "My Photos" --collection
        cl-client store create --label "Beach Sunset" --file sunset.jpg
        cl-client store create --label "Vacation" --description "Summer 2024" --file photo.jpg --parent-id 5
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            result = await manager.create_entity(
                label=label,
                description=description,
                is_collection=collection,
                parent_id=parent_id,
                image_path=file,
            )

            if result.is_error:
                console.print(f"[red]Error: {result.error}[/red]")
                sys.exit(1)

            if result.data is None:
                console.print("[red]Error: No data returned[/red]")
                sys.exit(1)

            entity = result.data
            console.print(f"[green]✓ Created entity [ID: {entity.id}][/green]")

            table = Table(title=f"Entity {entity.id}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Label", entity.label or "(no label)")
            table.add_row("Type", "Collection" if entity.is_collection else "Media")
            if entity.description:
                table.add_row("Description", entity.description)
            if entity.parent_id:
                table.add_row("Parent ID", str(entity.parent_id))
            if entity.file_path:
                table.add_row("File", entity.file_path)
                table.add_row("Size", f"{entity.file_size} bytes")
                table.add_row("Dimensions", f"{entity.width}x{entity.height}")
                table.add_row("MD5", entity.md5 or "")

            console.print(table)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@store.command("get")
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
    ctx: click.Context, entity_id: int, version: Optional[int], output: Optional[Path]
):
    """Get entity by ID (optionally specific version).

    Examples:
        cl-client store get 123
        cl-client store get 123 --version 2
        cl-client store get 123 --output entity.json
    """
    import json

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            result = await manager.read_entity(entity_id=entity_id, version=version)

            if result.is_error:
                console.print(f"[red]Error: {result.error}[/red]")
                sys.exit(1)

            if result.data is None:
                console.print("[red]Error: No data returned[/red]")
                sys.exit(1)

            entity = result.data
            table = Table(title=f"Entity {entity.id}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("ID", str(entity.id))
            table.add_row("Label", entity.label or "(no label)")
            table.add_row("Description", entity.description or "")
            table.add_row("Type", "Collection" if entity.is_collection else "Media")
            table.add_row(
                "Parent ID", str(entity.parent_id) if entity.parent_id else "-"
            )
            table.add_row(
                "Created",
                str(entity.create_date_datetime) if entity.create_date_datetime else "",
            )
            table.add_row(
                "Updated",
                (
                    str(entity.updated_date_datetime)
                    if entity.updated_date_datetime
                    else ""
                ),
            )
            table.add_row("Deleted", "Yes" if entity.is_deleted else "No")

            if not entity.is_collection and entity.file_size:
                table.add_row("File Size", f"{entity.file_size} bytes")
                table.add_row("Dimensions", f"{entity.width}x{entity.height}")
                table.add_row("MIME Type", entity.mime_type or "")
                table.add_row("MD5", entity.md5 or "")

            console.print(table)

            if output:
                with open(output, "w") as f:
                    json.dump(entity.model_dump(), f, indent=2, default=str)
                console.print(f"\n[green]✓ Saved to {output}[/green]")
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@store.command("update")
@click.argument("entity_id", type=int)
@click.option("--label", required=True, help="New label")
@click.option("--description", help="New description")
@click.option("--collection", is_flag=True, help="Set as collection")
@click.option("--parent-id", type=int, help="New parent collection ID")
@click.option(
    "--file", type=click.Path(exists=True, path_type=Path), help="New media file"
)
@click.pass_context
def update_entity(
    ctx: click.Context,
    entity_id: int,
    label: str,
    description: Optional[str],
    collection: bool,
    parent_id: Optional[int],
    file: Optional[Path],
):
    """Full update of an entity (requires label).

    Examples:
        cl-client store update 123 --label "Updated Label"
        cl-client store update 123 --label "New Title" --description "Updated desc"
        cl-client store update 123 --label "Photo" --file new_photo.jpg
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            result = await manager.update_entity(
                entity_id=entity_id,
                label=label,
                description=description,
                is_collection=collection,
                parent_id=parent_id,
                image_path=file,
            )

            if result.is_error:
                console.print(f"[red]Error: {result.error}[/red]")
                sys.exit(1)

            console.print(f"[green]✓ Updated entity [ID: {entity_id}][/green]")
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@store.command("patch")
@click.argument("entity_id", type=int)
@click.option("--label", help="Update label")
@click.option("--description", help="Update description")
@click.option("--parent-id", type=int, help="Update parent ID")
@click.option(
    "--delete", "soft_delete", is_flag=True, help="Soft delete (set is_deleted=true)"
)
@click.option("--restore", is_flag=True, help="Restore (set is_deleted=false)")
@click.pass_context
def patch_entity(
    ctx: click.Context,
    entity_id: int,
    label: Optional[str],
    description: Optional[str],
    parent_id: Optional[int],
    soft_delete: bool,
    restore: bool,
):
    """Partial update of an entity (only update specified fields).

    Examples:
        cl-client store patch 123 --label "New Label"
        cl-client store patch 123 --description "Updated description"
        cl-client store patch 123 --delete
        cl-client store patch 123 --restore
    """
    if soft_delete and restore:
        console.print("[red]Error: Cannot use both --delete and --restore[/red]")
        sys.exit(1)

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            is_deleted = None
            if soft_delete:
                is_deleted = True
            elif restore:
                is_deleted = False

            result = await manager.patch_entity(
                entity_id=entity_id,
                label=label,
                description=description,
                parent_id=parent_id,
                is_deleted=is_deleted,
            )

            if result.is_error:
                console.print(f"[red]Error: {result.error}[/red]")
                sys.exit(1)

            action = "Deleted" if soft_delete else "Restored" if restore else "Updated"
            console.print(f"[green]✓ {action} entity [ID: {entity_id}][/green]")
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@store.command("delete")
@click.argument("entity_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete_entity(ctx: click.Context, entity_id: int, yes: bool):
    """Permanently delete an entity (hard delete).

    Examples:
        cl-client store delete 123
        cl-client store delete 123 --yes  # Skip confirmation
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            # Get entity details first for confirmation
            if not yes:
                read_result = await manager.read_entity(entity_id=entity_id)
                if read_result.is_error:
                    console.print(f"[red]Error: {read_result.error}[/red]")
                    sys.exit(1)

                if read_result.data is None:
                    console.print("[red]Error: No data returned[/red]")
                    sys.exit(1)

                entity = read_result.data
                click.confirm(
                    f"Are you sure you want to permanently delete entity '{entity.label or '(no label)'}' (ID: {entity_id})?",
                    abort=True,
                )

            result = await manager.delete_entity(entity_id=entity_id)

            if result.is_error:
                console.print(f"[red]Error: {result.error}[/red]")
                sys.exit(1)

            console.print(f"[green]✓ Deleted entity [ID: {entity_id}][/green]")
        except click.Abort:
            console.print("[yellow]Deletion cancelled[/yellow]")
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@store.command("versions")
@click.argument("entity_id", type=int)
@click.option(
    "--output", "-o", type=click.Path(path_type=Path), help="Save versions to JSON file"
)
@click.pass_context
def get_versions(ctx: click.Context, entity_id: int, output: Optional[Path]):
    """Get version history for an entity.

    Examples:
        cl-client store versions 123
        cl-client store versions 123 --output versions.json
    """
    import json

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            result = await manager.get_versions(entity_id=entity_id)

            if result.is_error:
                console.print(f"[red]Error: {result.error}[/red]")
                sys.exit(1)

            if result.data is None:
                console.print("[red]Error: No data returned[/red]")
                sys.exit(1)

            versions = result.data
            console.print(f"[bold]Version history for entity [ID: {entity_id}][/bold]")
            console.print(f"Total versions: {len(versions)}\n")

            if versions:
                table = Table(title="Versions")
                table.add_column("Version", style="cyan")
                table.add_column("Label", style="green")
                table.add_column("Operation", style="magenta")
                table.add_column("Transaction", style="yellow")

                for v in versions:
                    table.add_row(
                        str(v.version),
                        v.label or "(no label)",
                        v.operation_type or "",
                        str(v.transaction_id),
                    )

                console.print(table)
            else:
                console.print("[yellow]No version history found[/yellow]")

            if output:
                with open(output, "w") as f:
                    json.dump(
                        [v.model_dump() for v in versions], f, indent=2, default=str
                    )
                console.print(f"\n[green]✓ Saved to {output}[/green]")
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@store.command("jobs")
@click.argument("entity_id", type=int)
@click.pass_context
def get_entity_jobs(ctx: click.Context, entity_id: int):
    """Get job status for an entity's embeddings.

    Shows the status of all compute jobs (face detection, face embedding,
    CLIP embedding) for the specified entity.

    Examples:
        cl-client store jobs 123
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            # Access the store client directly for database methods
            jobs = await manager.store_client.get_entity_jobs(entity_id=entity_id)

            console.print(f"[bold]Entity Jobs for ID: {entity_id}[/bold]")
            console.print(f"Total jobs: {len(jobs)}\n")

            if jobs:
                table = Table(title="Jobs")
                table.add_column("Job ID", style="cyan")
                table.add_column("Task Type", style="green")
                table.add_column("Status", style="magenta")
                table.add_column("Created", style="yellow")
                table.add_column("Error", style="red")

                for job in jobs:
                    # Status color based on job status
                    status_text = job.status
                    if job.status == "completed":
                        status_text = f"[green]{job.status}[/green]"
                    elif job.status == "failed":
                        status_text = f"[red]{job.status}[/red]"
                    elif job.status in ("queued", "in_progress"):
                        status_text = f"[yellow]{job.status}[/yellow]"

                    table.add_row(
                        job.job_id[:16] + "..." if len(job.job_id) > 16 else job.job_id,
                        job.task_type,
                        status_text,
                        str(job.created_at_datetime),
                        job.error_message or "",
                    )

                console.print(table)
            else:
                console.print("[yellow]No jobs found for this entity[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


# Store Admin Commands


@store.group("admin")
def store_admin():
    """Admin operations for store configuration."""
    pass


@store_admin.command("config")
@click.pass_context
def get_config(ctx: click.Context):
    """Get store configuration (admin only).

    Examples:
        cl-client --username admin --password admin store admin config
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            result = await manager.get_config()

            if result.is_error:
                console.print(f"[red]Error: {result.error}[/red]")
                sys.exit(1)

            if result.data is None:
                console.print("[red]Error: No data returned[/red]")
                sys.exit(1)

            config = result.data
            table = Table(title="Store Configuration")
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Guest Mode", "Enabled" if config.guest_mode else "Disabled")
            table.add_row(
                "Updated At",
                str(config.updated_at_datetime) if config.updated_at_datetime else "",
            )
            table.add_row("Updated By", config.updated_by or "")

            console.print(table)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@store_admin.command("set-guest-mode")
@click.argument("enabled", type=bool)
@click.pass_context
def set_guest_mode(ctx: click.Context, enabled: bool):
    """Enable or disable guest mode (admin only).

    Guest mode allows unauthenticated access to the store service.

    Examples:
        cl-client store admin set-guest-mode true
        cl-client store admin set-guest-mode false
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            result = await manager.update_guest_mode(guest_mode=enabled)

            if result.is_error:
                console.print(f"[red]Error: {result.error}[/red]")
                sys.exit(1)

            console.print(
                f"[green]✓ Guest mode {'enabled' if enabled else 'disabled'}[/green]"
            )
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


# CLIP Embedding Commands


@cli.group()
def clip_embedding():
    """CLIP image embedding operations."""
    pass


@clip_embedding.command()
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option("--watch", "-w", is_flag=True, help="Watch progress in real-time")
@click.option("--timeout", "-t", default=60.0, help="Timeout in seconds")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Download embedding to this file",
)
@click.pass_context
def embed(  # type: ignore[reportRedeclaration]
    ctx: click.Context, image: Path, watch: bool, timeout: float, output: Optional[Path]
):
    """Generate CLIP embedding for an image.

    Returns 512-dimensional embedding vector.

    Examples:
        cl-client clip-embedding embed image.jpg --output embedding.npy
        cl-client clip-embedding embed image.jpg --watch -o result.npy
        cl-client --username user --password pass clip-embedding embed image.jpg
    """

    async def run():
        client = await get_client(ctx)
        try:
            if watch:
                # Real-time progress with MQTT
                tracker = JobProgressTracker(
                    job_id="pending", description=f"CLIP embedding: {image.name}"
                )
                with tracker:
                    job = await client.clip_embedding.embed_image(
                        image=image,
                        on_progress=tracker.on_progress,
                        on_complete=tracker.on_complete,
                    )
                    tracker.job_id = job.job_id
                    final_job = await tracker.wait(timeout=timeout)

                if final_job and final_job.status == "completed":
                    console.print("[green]✓ Embedding generated successfully[/green]")
                    print_job_result(final_job)

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
                        console.print(f"[green]✓ Downloaded to {output}[/green]")

                elif final_job:
                    console.print(f"[red]✗ Job failed: {final_job.error_message}[/red]")
                    sys.exit(1)
            else:
                # Simple polling
                with console.status(f"[bold green]Processing {image.name}..."):
                    job = await client.clip_embedding.embed_image(
                        image=image,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(job)

                    # Download if output specified
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")

                else:
                    console.print(f"[red]✗ Failed: {job.error_message}[/red]")
                    sys.exit(1)
        finally:
            await client.close()
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


# Media Thumbnail Commands


@cli.group()
def media_thumbnail():
    """Media thumbnail generation."""
    pass


@media_thumbnail.command()
@click.argument("media", type=click.Path(exists=True, path_type=Path))
@click.option("--width", "-w", type=int, required=True, help="Thumbnail width")
@click.option("--height", "-h", type=int, required=True, help="Thumbnail height")
@click.option("--watch", is_flag=True, help="Watch progress in real-time")
@click.option("--timeout", "-t", default=60.0, help="Timeout in seconds")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Download thumbnail to this file",
)
@click.pass_context
def generate(
    ctx: click.Context,
    media: Path,
    width: int,
    height: int,
    watch: bool,
    timeout: float,
    output: Optional[Path],
):
    """Generate thumbnail for image or video.

    Examples:
      cl-client media-thumbnail generate video.mp4 -w 256 -h 256
      cl-client media-thumbnail generate image.jpg -w 128 -h 128 --watch -o thumb.jpg
    """

    async def run():
        client = await get_client(ctx)
        try:
            if watch:
                tracker = JobProgressTracker(
                    job_id="pending",
                    description=f"Thumbnail: {media.name} ({width}x{height})",
                )
                with tracker:
                    job = await client.media_thumbnail.generate(
                        media=media,
                        width=width,
                        height=height,
                        on_progress=tracker.on_progress,
                        on_complete=tracker.on_complete,
                    )
                    tracker.job_id = job.job_id
                    final_job = await tracker.wait(timeout=timeout)

                if final_job and final_job.status == "completed":
                    console.print("[green]✓ Thumbnail generated[/green]")
                    print_job_result(final_job)

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
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                elif final_job:
                    console.print(f"[red]✗ Failed: {final_job.error_message}[/red]")
                    sys.exit(1)
            else:
                with console.status("[bold green]Generating thumbnail..."):
                    job = await client.media_thumbnail.generate(
                        media=media,
                        width=width,
                        height=height,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(job)

                    # Download if output specified
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    console.print(f"[red]✗ Failed: {job.error_message}[/red]")
                    sys.exit(1)
        finally:
            await client.close()
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


# Hash Commands


@cli.group()
def hash():
    """Perceptual image hashing."""
    pass


@hash.command()
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option("--watch", is_flag=True, help="Watch progress in real-time")
@click.option("--timeout", "-t", default=30.0, help="Timeout in seconds")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Download hash output to this file",
)
@click.pass_context
def compute(
    ctx: click.Context, image: Path, watch: bool, timeout: float, output: Optional[Path]
):
    """Compute perceptual hash for an image.

    Returns phash, dhash, and other hash values.
    """

    async def run():
        client = await get_client(ctx)
        try:
            if watch:
                tracker = JobProgressTracker(
                    job_id="pending", description=f"Hashing: {image.name}"
                )
                with tracker:
                    job = await client.hash.compute(
                        image=image,
                        on_progress=tracker.on_progress,
                        on_complete=tracker.on_complete,
                    )
                    tracker.job_id = job.job_id
                    final_job = await tracker.wait(timeout=timeout)

                if final_job and final_job.status == "completed":
                    console.print("[green]✓ Hash computed[/green]")
                    print_job_result(final_job)

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
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                elif final_job:
                    console.print(f"[red]✗ Failed: {final_job.error_message}[/red]")
                    sys.exit(1)
            else:
                with console.status("[bold green]Computing hash..."):
                    job = await client.hash.compute(
                        image=image,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(job)

                    # Download if output specified
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    console.print(f"[red]✗ Failed: {job.error_message}[/red]")
                    sys.exit(1)
        finally:
            await client.close()
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


# EXIF Commands


@cli.group()
def exif():
    """EXIF metadata extraction."""
    pass


@exif.command()
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
    ctx: click.Context, image: Path, watch: bool, timeout: float, output: Optional[Path]
):
    """Extract EXIF metadata from an image."""

    async def run():
        client = await get_client(ctx)
        try:
            if watch:
                tracker = JobProgressTracker(
                    job_id="pending", description=f"EXIF extraction: {image.name}"
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
                    console.print("[green]✓ EXIF extracted[/green]")
                    print_job_result(final_job)

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
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                elif final_job:
                    console.print(f"[red]✗ Failed: {final_job.error_message}[/red]")
                    sys.exit(1)
            else:
                with console.status("[bold green]Extracting EXIF..."):
                    job = await client.exif.extract(
                        image=image,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(job)

                    # Download if output specified
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    console.print(f"[red]✗ Failed: {job.error_message}[/red]")
                    sys.exit(1)
        finally:
            await client.close()
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


# Face Detection Commands


@cli.group()
def face_detection():
    """Face detection operations."""
    pass


@face_detection.command()
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option("--watch", is_flag=True, help="Watch progress in real-time")
@click.option("--timeout", "-t", default=30.0, help="Timeout in seconds")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Download face detection output to this file",
)
@click.pass_context
def detect(
    ctx: click.Context, image: Path, watch: bool, timeout: float, output: Optional[Path]
):
    """Detect faces in an image."""

    async def run():
        client = await get_client(ctx)
        try:
            if watch:
                tracker = JobProgressTracker(
                    job_id="pending", description=f"Face detection: {image.name}"
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
                    console.print("[green]✓ Faces detected[/green]")
                    print_job_result(final_job)

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
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                elif final_job:
                    console.print(f"[red]✗ Failed: {final_job.error_message}[/red]")
                    sys.exit(1)
            else:
                with console.status("[bold green]Detecting faces..."):
                    job = await client.face_detection.detect(
                        image=image,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(job)

                    # Download if output specified
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    console.print(f"[red]✗ Failed: {job.error_message}[/red]")
                    sys.exit(1)
        finally:
            await client.close()
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


# Image Conversion Commands


@cli.group()
def image_conversion():
    """Image format conversion."""
    pass


@image_conversion.command()
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
    output: Optional[Path],
):
    """Convert image to different format.

    Examples:
      cl-client image-conversion convert photo.png -f jpg -q 90
      cl-client image-conversion convert image.jpg -f webp --watch
    """

    async def run():
        client = await get_client(ctx)
        try:
            if watch:
                tracker = JobProgressTracker(
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
                    console.print("[green]✓ Conversion completed[/green]")
                    print_job_result(final_job)
                    if (
                        output
                        and final_job.params
                        and "output_path" in final_job.params
                    ):
                        output_path = final_job.params["output_path"]
                        await client.download_job_file(
                            final_job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                elif final_job:
                    console.print(f"[red]✗ Failed: {final_job.error_message}[/red]")
                    sys.exit(1)
            else:
                with console.status("[bold green]Converting..."):
                    job = await client.image_conversion.convert(
                        image=image,
                        output_format=output_format,
                        quality=quality,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(job)
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    console.print(f"[red]✗ Failed: {job.error_message}[/red]")
                    sys.exit(1)
        finally:
            await client.close()
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


if __name__ == "__main__":
    cli()


# DINO Embedding Commands


@cli.group()
def dino_embedding():
    """DINO image embedding operations."""
    pass


@dino_embedding.command()
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
def embed(  # type: ignore[reportRedeclaration]
    ctx: click.Context, image: Path, watch: bool, timeout: float, output: Optional[Path]
):
    """Generate DINO embedding for an image.

    Returns 384-dimensional embedding vector.
    """

    async def run():
        client = await get_client(ctx)
        try:
            if watch:
                tracker = JobProgressTracker(
                    job_id="pending", description=f"DINO embedding: {image.name}"
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
                    console.print("[green]✓ Embedding generated[/green]")
                    print_job_result(final_job)
                    if (
                        output
                        and final_job.params
                        and "output_path" in final_job.params
                    ):
                        output_path = final_job.params["output_path"]
                        await client.download_job_file(
                            final_job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                elif final_job:
                    console.print(f"[red]✗ Failed: {final_job.error_message}[/red]")
                    sys.exit(1)
            else:
                with console.status("[bold green]Processing..."):
                    job = await client.dino_embedding.embed_image(
                        image=image,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(job)
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    console.print(f"[red]✗ Failed: {job.error_message}[/red]")
                    sys.exit(1)
        finally:
            await client.close()
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


# Face Embedding Commands


@cli.group()
def face_embedding():
    """Face embedding operations."""
    pass


@face_embedding.command()
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option("--watch", is_flag=True, help="Watch progress in real-time")
@click.option("--timeout", "-t", default=60.0, help="Timeout in seconds")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Download output to this file",
)
@click.pass_context
def embed(
    ctx: click.Context, image: Path, watch: bool, timeout: float, output: Optional[Path]
):
    """Generate face embeddings for an image."""

    async def run():
        client = await get_client(ctx)
        try:
            if watch:
                tracker = JobProgressTracker(
                    job_id="pending", description=f"Face embedding: {image.name}"
                )
                with tracker:
                    job = await client.face_embedding.embed_faces(
                        image=image,
                        on_progress=tracker.on_progress,
                        on_complete=tracker.on_complete,
                    )
                    tracker.job_id = job.job_id
                    final_job = await tracker.wait(timeout=timeout)

                if final_job and final_job.status == "completed":
                    console.print("[green]✓ Embeddings generated[/green]")
                    print_job_result(final_job)
                    if (
                        output
                        and final_job.params
                        and "output_path" in final_job.params
                    ):
                        output_path = final_job.params["output_path"]
                        await client.download_job_file(
                            final_job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                elif final_job:
                    console.print(f"[red]✗ Failed: {final_job.error_message}[/red]")
                    sys.exit(1)
            else:
                with console.status("[bold green]Processing..."):
                    job = await client.face_embedding.embed_faces(
                        image=image,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(job)
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    console.print(f"[red]✗ Failed: {job.error_message}[/red]")
                    sys.exit(1)
        finally:
            await client.close()
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


# HLS Streaming Commands


@cli.group()
def hls_streaming():
    """HLS manifest generation for video streaming."""
    pass


@hls_streaming.command()
@click.argument("video", type=click.Path(exists=True, path_type=Path))
@click.option("--watch", is_flag=True, help="Watch progress in real-time")
@click.option("--timeout", "-t", default=120.0, help="Timeout in seconds")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Download output to this file",
)
@click.pass_context
def generate_manifest(
    ctx: click.Context, video: Path, watch: bool, timeout: float, output: Optional[Path]
):
    """Generate HLS manifest for a video file.

    Creates master playlist and variant playlists for adaptive streaming.
    """

    async def run():
        client = await get_client(ctx)
        try:
            if watch:
                tracker = JobProgressTracker(
                    job_id="pending", description=f"HLS manifest: {video.name}"
                )
                with tracker:
                    job = await client.hls_streaming.generate_manifest(
                        video=video,
                        on_progress=tracker.on_progress,
                        on_complete=tracker.on_complete,
                    )
                    tracker.job_id = job.job_id
                    final_job = await tracker.wait(timeout=timeout)

                if final_job and final_job.status == "completed":
                    console.print("[green]✓ HLS manifest generated[/green]")
                    print_job_result(final_job)
                    if (
                        output
                        and final_job.params
                        and "output_path" in final_job.params
                    ):
                        output_path = final_job.params["output_path"]
                        await client.download_job_file(
                            final_job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                elif final_job:
                    console.print(f"[red]✗ Failed: {final_job.error_message}[/red]")
                    sys.exit(1)
            else:
                with console.status("[bold green]Generating HLS manifest..."):
                    job = await client.hls_streaming.generate_manifest(
                        video=video,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(job)
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    console.print(f"[red]✗ Failed: {job.error_message}[/red]")
                    sys.exit(1)
        finally:
            await client.close()
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


# Face Database Commands


@cli.group()
def faces():
    """Face detection and similarity search commands."""
    pass


@faces.command("list")
@click.argument("entity_id", type=int)
@click.pass_context
def list_faces(ctx: click.Context, entity_id: int):
    """List all faces detected in an entity.

    Examples:
        cl-client faces list 123
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            faces = await manager.store_client.get_entity_faces(entity_id=entity_id)

            console.print(f"[bold]Faces in Entity ID: {entity_id}[/bold]")
            console.print(f"Total faces: {len(faces)}\n")

            if faces:
                table = Table(title="Detected Faces")
                table.add_column("Face ID", style="cyan")
                table.add_column("Confidence", style="green")
                table.add_column("BBox (x1,y1,x2,y2)", style="yellow")
                table.add_column("Known Person", style="magenta")
                table.add_column("Created", style="white")

                for face in faces:
                    bbox_str = f"({face.bbox.x1:.0f},{face.bbox.y1:.0f},{face.bbox.x2:.0f},{face.bbox.y2:.0f})"
                    person_str = (
                        str(face.known_person_id) if face.known_person_id else "Unknown"
                    )

                    table.add_row(
                        str(face.id),
                        f"{face.confidence:.2f}",
                        bbox_str,
                        person_str,
                        str(face.created_at_datetime),
                    )

                console.print(table)
            else:
                console.print("[yellow]No faces found in this entity[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@faces.command("similar")
@click.argument("face_id", type=int)
@click.option("--limit", "-l", default=10, help="Maximum number of results")
@click.option(
    "--threshold",
    "-t",
    default=0.7,
    type=float,
    help="Minimum similarity score (0.0-1.0)",
)
@click.pass_context
def find_similar_faces(ctx: click.Context, face_id: int, limit: int, threshold: float):
    """Find faces similar to the specified face.

    Examples:
        cl-client faces similar 456
        cl-client faces similar 456 --limit 5 --threshold 0.8
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            response = await manager.store_client.find_similar_faces(
                face_id=face_id,
                limit=limit,
                threshold=threshold,
            )

            console.print(f"[bold]Similar Faces for Face ID: {face_id}[/bold]")
            console.print(f"Found {len(response.results)} similar faces\n")

            if response.results:
                table = Table(title=f"Similar Faces (threshold >= {threshold})")
                table.add_column("Face ID", style="cyan")
                table.add_column("Similarity Score", style="green")

                for result in response.results:
                    table.add_row(
                        str(result.face_id),
                        f"{result.score:.4f}",
                    )

                console.print(table)
            else:
                console.print(
                    f"[yellow]No similar faces found (threshold: {threshold})[/yellow]"
                )
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@faces.command("download-embedding")
@click.argument("face_id", type=int)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    required=True,
    help="Output file path",
)
@click.pass_context
def download_face_embedding(ctx: click.Context, face_id: int, output: Path):
    """Download face embedding as NPY file.

    Examples:
        cl-client faces download-embedding 456 --output face_456.npy
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            await manager.store_client.download_face_embedding(
                face_id=face_id,
                dest=output,
            )
            console.print(f"[green]✓ Face embedding downloaded to {output}[/green]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@faces.command("matches")
@click.argument("face_id", type=int)
@click.pass_context
def get_face_matches(ctx: click.Context, face_id: int):
    """Get face match history for a face.

    Examples:
        cl-client faces matches 456
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            matches = await manager.store_client.get_face_matches(face_id=face_id)

            console.print(f"[bold]Match History for Face ID: {face_id}[/bold]")
            console.print(f"Total matches: {len(matches)}\n")

            if matches:
                table = Table(title="Face Matches")
                table.add_column("Match ID", style="cyan")
                table.add_column("Matched Face ID", style="green")
                table.add_column("Similarity", style="yellow")
                table.add_column("Created", style="white")

                for match in matches:
                    table.add_row(
                        str(match.id),
                        str(match.matched_face_id),
                        f"{match.similarity_score:.4f}",
                        str(match.created_at_datetime),
                    )

                console.print(table)
            else:
                console.print("[yellow]No match history found[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


# Known Persons Commands


@cli.group()
def persons():
    """Known persons management commands."""
    pass


@persons.command("list")
@click.pass_context
def list_persons(ctx: click.Context):
    """List all known persons.

    Examples:
        cl-client persons list
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            persons = await manager.store_client.get_all_known_persons()

            console.print(f"[bold]Known Persons[/bold]")
            console.print(f"Total persons: {len(persons)}\n")

            if persons:
                table = Table(title="Known Persons")
                table.add_column("Person ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Face Count", style="yellow")
                table.add_column("Created", style="white")

                for person in persons:
                    table.add_row(
                        str(person.id),
                        person.name or "(no name)",
                        (
                            str(person.face_count)
                            if person.face_count is not None
                            else "N/A"
                        ),
                        str(person.created_at_datetime),
                    )

                console.print(table)
            else:
                console.print("[yellow]No known persons found[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@persons.command("get")
@click.argument("person_id", type=int)
@click.pass_context
def get_person(ctx: click.Context, person_id: int):
    """Get details for a known person.

    Examples:
        cl-client persons get 789
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            person = await manager.store_client.get_known_person(person_id=person_id)

            console.print(f"[bold]Person ID: {person.id}[/bold]\n")

            table = Table(title="Person Details")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Name", person.name or "(no name)")
            table.add_row(
                "Face Count",
                str(person.face_count) if person.face_count is not None else "N/A",
            )
            table.add_row("Created", str(person.created_at_datetime))
            table.add_row("Updated", str(person.updated_at_datetime))

            console.print(table)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@persons.command("update")
@click.argument("person_id", type=int)
@click.option("--name", "-n", required=True, help="New name for the person")
@click.pass_context
def update_person(ctx: click.Context, person_id: int, name: str):
    """Update a known person's name.

    Examples:
        cl-client persons update 789 --name "John Doe"
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            person = await manager.store_client.update_known_person_name(
                person_id=person_id,
                name=name,
            )

            console.print(f"[green]✓ Updated person {person_id}[/green]")
            console.print(f"New name: {person.name}")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@persons.command("faces")
@click.argument("person_id", type=int)
@click.pass_context
def get_person_faces(ctx: click.Context, person_id: int):
    """List all faces for a known person.

    Examples:
        cl-client persons faces 789
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            faces = await manager.store_client.get_known_person_faces(
                person_id=person_id
            )

            console.print(f"[bold]Faces for Person ID: {person_id}[/bold]")
            console.print(f"Total faces: {len(faces)}\n")

            if faces:
                table = Table(title="Person Faces")
                table.add_column("Face ID", style="cyan")
                table.add_column("Entity ID", style="green")
                table.add_column("Confidence", style="yellow")
                table.add_column("BBox (x1,y1,x2,y2)", style="magenta")
                table.add_column("Created", style="white")

                for face in faces:
                    bbox_str = f"({face.bbox.x1:.0f},{face.bbox.y1:.0f},{face.bbox.x2:.0f},{face.bbox.y2:.0f})"

                    table.add_row(
                        str(face.id),
                        str(face.entity_id),
                        f"{face.confidence:.2f}",
                        bbox_str,
                        str(face.created_at_datetime),
                    )

                console.print(table)
            else:
                console.print("[yellow]No faces found for this person[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


# Image Similarity Commands


@cli.group()
def images():
    """Image similarity search commands (CLIP-based)."""
    pass


@images.command("similar")
@click.argument("entity_id", type=int)
@click.option("--limit", "-l", default=10, help="Maximum number of results")
@click.option(
    "--threshold",
    "-t",
    default=0.85,
    type=float,
    help="Minimum similarity score (0.0-1.0)",
)
@click.option("--details", is_flag=True, help="Include full entity details in results")
@click.pass_context
def find_similar_images(
    ctx: click.Context, entity_id: int, limit: int, threshold: float, details: bool
):
    """Find images similar to the specified entity.

    Uses CLIP embeddings for semantic similarity search.

    Examples:
        cl-client images similar 123
        cl-client images similar 123 --limit 5 --threshold 0.9
        cl-client images similar 123 --details
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            response = await manager.store_client.find_similar_images(
                entity_id=entity_id,
                limit=limit,
                score_threshold=threshold,
                include_details=details,
            )

            console.print(f"[bold]Similar Images for Entity ID: {entity_id}[/bold]")
            console.print(f"Found {len(response.results)} similar images\n")

            if response.results:
                table = Table(title=f"Similar Images (threshold >= {threshold})")
                table.add_column("Entity ID", style="cyan")
                table.add_column("Similarity Score", style="green")
                if details:
                    table.add_column("Label", style="yellow")

                for result in response.results:
                    if details and result.entity:
                        table.add_row(
                            str(result.entity_id),
                            f"{result.score:.4f}",
                            result.entity.label or "(no label)",
                        )
                    else:
                        table.add_row(
                            str(result.entity_id),
                            f"{result.score:.4f}",
                        )

                console.print(table)
            else:
                console.print(
                    f"[yellow]No similar images found (threshold: {threshold})[/yellow]"
                )
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@images.command("download-embedding")
@click.argument("entity_id", type=int)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    required=True,
    help="Output file path",
)
@click.pass_context
def download_entity_embedding(ctx: click.Context, entity_id: int, output: Path):
    """Download entity CLIP embedding as NPY file.

    Examples:
        cl-client images download-embedding 123 --output entity_123.npy
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            await manager.store_client.download_entity_embedding(
                entity_id=entity_id,
                dest=output,
            )
            console.print(
                f"[green]✓ Entity CLIP embedding downloaded to {output}[/green]"
            )
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())
