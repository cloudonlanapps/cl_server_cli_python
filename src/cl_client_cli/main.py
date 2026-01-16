"""CL Client CLI - Main command-line interface."""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import NoReturn, Optional

import click
from pydantic import BaseModel
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from cl_client import ComputeClient, SessionManager, ServerConfig, StoreManager
from cl_client.models import JobResponse

console = Console()


# ============================================================================
# CLI Response Models (minimal - rest use SDK models)
# ============================================================================


class ErrorResponse(BaseModel):
    """CLI error response model."""

    error: str
    status: str = "failed"


class SuccessResponse(BaseModel):
    """CLI success response model for void operations."""

    status: str = "success"
    message: Optional[str] = None


# ============================================================================
# CLI Exceptions
# ============================================================================


class CLIException(click.ClickException):
    """Custom exception for CLI errors with support for JSON formatting."""

    def __init__(self, ctx: click.Context, message: str):
        super().__init__(message)
        self.ctx = ctx

    def show(self, file: Optional[any] = None) -> None:
        """Format and display the error message."""
        error = ErrorResponse(error=self.message)
        if should_use_json(self.ctx):
            click.echo(error.model_dump_json(indent=2))
        else:
            # Human mode: just print error message to stderr
            click.echo(f"Error: {self.message}", err=True)


class JSONGroup(click.Group):
    """Custom Click Group to handle exceptions as JSON when --json flag is present."""

    def main(self, *args, **kwargs):
        # Check for --json flag in args
        # CliRunner calls main(args=..., standalone_mode=False)
        cmd_args = kwargs.get("args")
        
        # If passed as positional arg (unlikely but possible)
        if cmd_args is None and len(args) > 0:
            cmd_args = args[0]
        
        # Capture original standalone_mode intent (default is True)
        # We need to know if we should re-raise or print/exit for non-JSON mode
        original_standalone_mode = kwargs.get("standalone_mode", True)
        
        # Force standalone_mode=False so we can catch exceptions and process them
        kwargs["standalone_mode"] = False

        try:
            return super().main(*args, **kwargs)
        except click.ClickException as e:
            use_json = False
            if cmd_args is not None:
                # Check explicit args
                use_json = "--json" in cmd_args
            else:
                # Fallback to sys.argv (production usage)
                use_json = "--json" in sys.argv
            
            if use_json:
                error = ErrorResponse(error=str(e), status="failed")
                click.echo(error.model_dump_json(indent=2))
                sys.exit(e.exit_code)
            else:
                # Revert to original behavior
                if original_standalone_mode:
                    e.show()
                    sys.exit(e.exit_code)
                else:
                    raise


# ============================================================================
# Output Helper Functions
# ============================================================================


def should_use_json(ctx: click.Context) -> bool:
    """Check if JSON output is enabled."""
    return ctx.obj.get("output_json", False)


def output_sdk_result(ctx: click.Context, sdk_model: BaseModel) -> None:
    """Output SDK Pydantic model directly.

    Args:
        ctx: Click context
        sdk_model: Any Pydantic model from SDK (JobResponse, EntityListResult, etc.)
    """
    # Dump SDK model as JSON (both --json and human mode for now)
    click.echo(sdk_model.model_dump_json(indent=2, exclude_none=True))


def output_error(ctx: click.Context, error_message: str) -> NoReturn:
    """Output CLI error via custom exception.

    Args:
        ctx: Click context
        error_message: Error message to display
    """
    raise CLIException(ctx, error_message)


class JobProgressTracker:
    """Track job progress with optional display.

    When JSON mode is active, suppresses all stdout/stderr output.
    MQTT callbacks are still used internally regardless of JSON mode.
    """

    def __init__(self, ctx: click.Context, job_id: str, description: str):
        self.ctx = ctx
        self.job_id = job_id
        self.description = description
        self.use_json = should_use_json(ctx)
        self.completed = asyncio.Event()
        self.final_job: Optional[JobResponse] = None

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
                return self.final_job
            await asyncio.sleep(0.5)

        output_error(
            ctx=self.ctx, error_message=f"Job {self.job_id} timed out after {timeout}s"
        )


def print_job_result(ctx: click.Context, job: JobResponse) -> None:
    """Print job result using SDK JobResponse model.

    Args:
        ctx: Click context
        job: JobResponse from SDK (already a Pydantic model)
    """
    output_sdk_result(ctx, job)  # Just dump the SDK model!


@click.group(cls=JSONGroup)
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
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Output results as JSON (script-friendly)",
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
    output_json: bool,
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
    # Suppress Rich console output in JSON mode to ensure clean JSON stdout
    if output_json:
        global console
        console = Console(file=open(os.devnull, "w"))

    # Store config in context for commands to access
    ctx.ensure_object(dict)
    ctx.obj["username"] = username
    ctx.obj["password"] = password
    ctx.obj["auth_url"] = auth_url
    ctx.obj["compute_url"] = compute_url
    ctx.obj["store_url"] = store_url
    ctx.obj["no_auth"] = no_auth
    ctx.obj["output_json"] = output_json
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
        output_error(ctx, f"Authentication failed: {e}")


async def get_session_manager(ctx: click.Context) -> SessionManager:
    """Get authenticated SessionManager for admin operations.

    Raises:
        SystemExit if authentication fails or no credentials provided
    """
    username = ctx.obj.get("username")
    password = ctx.obj.get("password")
    server_config = ctx.obj.get("server_config")

    if not username or not password:
        output_error(
            ctx,
            "Username and password required for this operation. Use --username and --password flags or set CL_USERNAME and CL_PASSWORD env vars",
        )

    session = SessionManager(server_config=server_config)
    try:
        await session.login(username, password)
        return session
    except Exception as e:
        await session.close()
        output_error(ctx, f"Authentication failed: {e}")


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
        output_error(ctx, f"Authentication failed: {e}")


@click.group()
@click.pass_context
def compute(ctx: click.Context):
    """Manage and monitor compute service."""
    pass


@compute.command("capabilities")
@click.pass_context
def compute_capabilities(ctx: click.Context):
    """Show current worker capabilities and availability."""

    async def run():
        config = ctx.obj.get("server_config")
        if not config:
            output_error(ctx, "Server configuration not found in context.")
            return

        async with ComputeClient(server_config=config) as client:
            try:
                response = await client.get_capabilities()
                output_sdk_result(ctx, response)
            except Exception as e:
                output_error(ctx, str(e))

    asyncio.run(run())


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

            # Output the SDK User model directly
            output_sdk_result(ctx, user)
        except Exception as e:
            output_error(ctx, str(e))
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

            # For lists, output as JSON array directly
            click.echo(
                json.dumps(
                    [u.model_dump(mode="json", exclude_none=True) for u in users],
                    indent=2,
                )
            )
        except Exception as e:
            output_error(ctx, str(e))
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

            # Output SDK User model directly
            output_sdk_result(ctx, user)
        except Exception as e:
            output_error(ctx, str(e))
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

            # Output SDK User model directly
            output_sdk_result(ctx, user)
        except Exception as e:
            output_error(ctx, str(e))
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

            # Output success response for void operation
            success = SuccessResponse(
                message=f"User '{user.username}' deleted successfully"
            )
            output_sdk_result(ctx, success)
        except click.Abort:
            output_error(ctx, "Deletion cancelled")
        except Exception as e:
            output_error(ctx, str(e))
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

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            result = await manager.list_entities(
                page=page,
                page_size=page_size,
                search_query=search,
            )

            if result.is_error or result.data is None:
                output_error(
                    ctx, str(result.error) if result.is_error else "No data returned"
                )

            # Output SDK EntityListResult model directly
            output_sdk_result(ctx, result.data)

            # Save to file if requested (works in both JSON and human mode)
            if output:
                with open(output, "w") as f:
                    json.dump(result.data.model_dump(), f, indent=2, default=str)
                if not should_use_json(ctx):
                    click.echo(f"Saved to {output}", err=True)
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

            if result.is_error or result.data is None:
                output_error(
                    ctx, str(result.error) if result.is_error else "No data returned"
                )

            # Output SDK EntityResult model directly
            output_sdk_result(ctx, result.data)
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

            if result.is_error or result.data is None:
                output_error(
                    ctx, str(result.error) if result.is_error else "No data returned"
                )

            # Output SDK EntityResult model directly
            output_sdk_result(ctx, result.data)

            # Save to file if requested
            if output:
                with open(output, "w") as f:
                    json.dump(result.data.model_dump(), f, indent=2, default=str)
                if not should_use_json(ctx):
                    click.echo(f"Saved to {output}", err=True)
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
                output_error(ctx, str(result.error))

            # Output success response for void operation
            success = SuccessResponse(message=f"Updated entity [ID: {entity_id}]")
            output_sdk_result(ctx, success)
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
        output_error(ctx, "Cannot use both --delete and --restore")

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
                output_error(ctx, str(result.error))

            # Output success response for void operation
            action = "Deleted" if soft_delete else "Restored" if restore else "Updated"
            success = SuccessResponse(message=f"{action} entity [ID: {entity_id}]")
            output_sdk_result(ctx, success)
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
                    output_error(ctx, str(read_result.error))

                if read_result.data is None:
                    output_error(ctx, "No data returned")

                entity = read_result.data
                entity_label = entity.label if entity.label else "(no label)"
                click.confirm(
                    f"Are you sure you want to permanently delete entity '{entity_label}' (ID: {entity_id})?",
                    abort=True,
                )

            result = await manager.delete_entity(entity_id=entity_id)

            if result.is_error:
                output_error(ctx, str(result.error))

            # Output success response for void operation
            success = SuccessResponse(message=f"Deleted entity [ID: {entity_id}]")
            output_sdk_result(ctx, success)
        except click.Abort:
            output_error(ctx, "Deletion cancelled")
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

            if result.is_error or result.data is None:
                output_error(
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
                if not should_use_json(ctx):
                    click.echo(f"Saved to {output}", err=True)
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

            # Output SDK list of Job models as JSON array
            click.echo(
                json.dumps(
                    [j.model_dump(mode="json", exclude_none=True) for j in jobs],
                    indent=2,
                )
            )
        except Exception as e:
            output_error(ctx, str(e))
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

            if result.is_error or result.data is None:
                output_error(
                    ctx, str(result.error) if result.is_error else "No data returned"
                )

            # Output SDK Config model directly
            output_sdk_result(ctx, result.data)
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
                output_error(ctx, str(result.error))

            # Output success response for void operation
            success = SuccessResponse(
                message=f"Guest mode {'enabled' if enabled else 'disabled'}"
            )
            output_sdk_result(ctx, success)
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
                    ctx, job_id="pending", description=f"CLIP embedding: {image.name}"
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
                    print_job_result(ctx, final_job)

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
                        if not should_use_json(ctx):
                            click.echo(f"Downloaded to {output}", err=True)

                elif final_job:
                    output_error(ctx, f"Job failed: {final_job.error_message}")
            else:
                # Simple polling (suppress status in JSON mode)
                if not should_use_json(ctx):
                    with console.status(f"[bold green]Processing {image.name}..."):
                        job = await client.clip_embedding.embed_image(
                            image=image,
                            wait=True,
                            timeout=timeout,
                        )
                else:
                    job = await client.clip_embedding.embed_image(
                        image=image,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    print_job_result(ctx, job)

                    # Download if output specified
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        if not should_use_json(ctx):
                            click.echo(f"Downloaded to {output}", err=True)

                else:
                    output_error(ctx, f"Failed: {job.error_message}")
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
                    ctx,
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
                    print_job_result(ctx, final_job)

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
                    output_error(ctx, f"Failed: {final_job.error_message}")
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
                    print_job_result(ctx, job)

                    # Download if output specified
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    output_error(ctx, f"Failed: {job.error_message}")
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


@hash.command("compute")
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
def compute_hash(
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
                    ctx, job_id="pending", description=f"Hashing: {image.name}"
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
                    print_job_result(ctx, final_job)

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
                    output_error(ctx, f"Failed: {final_job.error_message}")
            else:
                with console.status("[bold green]Computing hash..."):
                    job = await client.hash.compute(
                        image=image,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(ctx, job)

                    # Download if output specified
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    output_error(ctx, f"Failed: {job.error_message}")
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
                    console.print("[green]✓ EXIF extracted[/green]")
                    print_job_result(ctx, final_job)

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
                    output_error(ctx, f"Failed: {final_job.error_message}")
            else:
                with console.status("[bold green]Extracting EXIF..."):
                    job = await client.exif.extract(
                        image=image,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(ctx, job)

                    # Download if output specified
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    output_error(ctx, f"Failed: {job.error_message}")
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
                    console.print("[green]✓ Faces detected[/green]")
                    print_job_result(ctx, final_job)

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
                    output_error(ctx, f"Failed: {final_job.error_message}")
            else:
                with console.status("[bold green]Detecting faces..."):
                    job = await client.face_detection.detect(
                        image=image,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(ctx, job)

                    # Download if output specified
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    output_error(ctx, f"Failed: {job.error_message}")
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
                    console.print("[green]✓ Conversion completed[/green]")
                    print_job_result(ctx, final_job)
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
                    output_error(ctx, f"Failed: {final_job.error_message}")
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
                    print_job_result(ctx, job)
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    output_error(ctx, f"Failed: {job.error_message}")
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
                    console.print("[green]✓ Embedding generated[/green]")
                    print_job_result(ctx, final_job)
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
                    output_error(ctx, f"Failed: {final_job.error_message}")
            else:
                with console.status("[bold green]Processing..."):
                    job = await client.dino_embedding.embed_image(
                        image=image,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(ctx, job)
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    output_error(ctx, f"Failed: {job.error_message}")
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
                    ctx, job_id="pending", description=f"Face embedding: {image.name}"
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
                    print_job_result(ctx, final_job)
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
                    output_error(ctx, f"Failed: {final_job.error_message}")
            else:
                with console.status("[bold green]Processing..."):
                    job = await client.face_embedding.embed_faces(
                        image=image,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(ctx, job)
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    output_error(ctx, f"Failed: {job.error_message}")
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
                    ctx, job_id="pending", description=f"HLS manifest: {video.name}"
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
                    print_job_result(ctx, final_job)
                    if (
                        output
                        and final_job.params
                        and "output_path" in final_job.params
                    ):
                        output_path = final_job.params["output_path"]
                        # For HLS, output_path is a directory, download the manifest
                        output_path = str(Path(output_path) / "adaptive.m3u8")
                        await client.download_job_file(
                            final_job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                elif final_job:
                    output_error(ctx, f"Failed: {final_job.error_message}")
            else:
                with console.status("[bold green]Generating HLS manifest..."):
                    job = await client.hls_streaming.generate_manifest(
                        video=video,
                        wait=True,
                        timeout=timeout,
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(ctx, job)
                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        # For HLS, output_path is a directory, download the manifest
                        output_path = str(Path(output_path) / "adaptive.m3u8")
                        await client.download_job_file(
                            job.job_id, str(output_path), output
                        )
                        console.print(f"[green]✓ Downloaded to {output}[/green]")
                else:
                    output_error(ctx, f"Failed: {job.error_message}")
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

            # Output SDK list of Face models as JSON array
            click.echo(
                json.dumps(
                    [f.model_dump(mode="json", exclude_none=True) for f in faces],
                    indent=2,
                )
            )
        except Exception as e:
            output_error(ctx, str(e))
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

            # Output SDK SimilaritySearchResponse model directly
            output_sdk_result(ctx, response)
        except Exception as e:
            output_error(ctx, str(e))
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
            # Output success response for download operation
            success = SuccessResponse(message=f"Face embedding downloaded to {output}")
            output_sdk_result(ctx, success)
        except Exception as e:
            output_error(ctx, str(e))
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

            # Output SDK list of FaceMatch models as JSON array
            click.echo(
                json.dumps(
                    [m.model_dump(mode="json", exclude_none=True) for m in matches],
                    indent=2,
                )
            )
        except Exception as e:
            output_error(ctx, str(e))
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

            # Output SDK list of KnownPerson models as JSON array
            click.echo(
                json.dumps(
                    [p.model_dump(mode="json", exclude_none=True) for p in persons],
                    indent=2,
                )
            )
        except Exception as e:
            output_error(ctx, str(e))
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

            # Output SDK KnownPerson model directly
            output_sdk_result(ctx, person)
        except Exception as e:
            output_error(ctx, str(e))
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

            # Output SDK KnownPerson model directly
            output_sdk_result(ctx, person)
        except Exception as e:
            output_error(ctx, str(e))
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

            # Output SDK list of Face models as JSON array
            click.echo(
                json.dumps(
                    [f.model_dump(mode="json", exclude_none=True) for f in faces],
                    indent=2,
                )
            )
        except Exception as e:
            output_error(ctx, str(e))
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

            # Output SDK SimilaritySearchResponse model directly
            output_sdk_result(ctx, response)
        except Exception as e:
            output_error(ctx, str(e))
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
            # Output success response for download operation
            success = SuccessResponse(
                message=f"Entity CLIP embedding downloaded to {output}"
            )
            output_sdk_result(ctx, success)
        except Exception as e:
            output_error(ctx, str(e))
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


cli.add_command(compute)
cli.add_command(store)
cli.add_command(user)
cli.add_command(face_detection)
cli.add_command(image_conversion)
cli.add_command(dino_embedding)
cli.add_command(face_embedding)
cli.add_command(hls_streaming)
cli.add_command(faces)
cli.add_command(persons)
cli.add_command(images)

if __name__ == "__main__":
    cli()
