"""CL Client CLI - Main command-line interface."""

import asyncio
import base64
import configparser
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import NoReturn, Optional

import click
from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from cl_client import (
    ComputeClient,
    ServerPref,
    SessionManager,
    StoreManager,
)
from cl_client.intelligence_models import EntityIntelligenceData
from cl_client.models import JobResponse
from cl_client.store_models import AuditReport, CleanupReport, StorePref

console = Console()


# ============================================================================
# Permissions Configuration
# ============================================================================

# Allowed permissions list - placeholder, update as needed
ALLOWED_PERMISSIONS = [
    "read:jobs",
    "write:jobs",
    "delete:jobs",
    "read:entities",
    "write:entities",
    "delete:entities",
    "admin:users",
    "admin:config",
    "admin:system",
]


def validate_permissions(permissions: tuple[str, ...]) -> tuple[bool, list[str]]:
    """Validate permissions against allowed list.

    Args:
        permissions: Tuple of permission strings to validate

    Returns:
        Tuple of (is_valid, list_of_invalid_permissions)
    """
    invalid = [p for p in permissions if p not in ALLOWED_PERMISSIONS]
    return (len(invalid) == 0, invalid)


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
# Configuration File Support
# ============================================================================


def load_config_file() -> dict[str, Optional[str]]:
    """Load configuration from ~/.cl_client_config.ini file.

    Config file format:
    [cl_client]
    auth_url = http://localhost:8010
    compute_url = http://localhost:8012
    store_url = http://localhost:8011
    mqtt_url = mqtt://localhost:1883
    username = admin
    # Note: password NOT stored in config for security

    Returns:
        Dictionary with config values (None if not set)
    """
    config_path = Path.home() / ".cl_client_config.ini"
    config = {
        "auth_url": None,
        "compute_url": None,
        "store_url": None,
        "mqtt_url": None,
        "username": None,
    }

    if config_path.exists():
        parser = configparser.ConfigParser()
        try:
            parser.read(config_path)
            if "cl_client" in parser:
                section = parser["cl_client"]
                for key in config.keys():
                    if key in section:
                        config[key] = section[key]
        except Exception as e:
            click.echo(f"Warning: Failed to read config file: {e}", err=True)

    return config


# ============================================================================
# Password Caching (Encrypted, 6-hour expiration)
# ============================================================================


def _get_encryption_key(username: str) -> bytes:
    """Generate encryption key from username and machine UUID.

    Uses a deterministic approach so the same key is generated across sessions.
    The key is derived from:
    1. Username (consistent for the user)
    2. Machine UUID (consistent for the machine)

    This provides reasonable security while avoiding storing the key in plaintext.
    """
    try:
        # Get machine UUID (consistent across sessions on the same machine)
        machine_id = str(uuid.getnode())
    except Exception:
        # Fallback if UUID not available
        machine_id = "default-machine"

    # Combine username and machine ID to create a unique key
    key_material = f"{username}:{machine_id}".encode()

    # Use SHA256 to derive a 32-byte key, then base64 encode for Fernet
    key_hash = hashlib.sha256(key_material).digest()
    return base64.urlsafe_b64encode(key_hash)


def save_password_to_cache(username: str, password: str) -> None:
    """Save encrypted password to cache file with timestamp.

    Args:
        username: Username for authentication
        password: Password to encrypt and cache
    """
    cache_path = Path.home() / ".cl_client_cache"

    try:
        # Generate encryption key
        key = _get_encryption_key(username)
        cipher = Fernet(key)

        # Encrypt password
        encrypted_password = cipher.encrypt(password.encode()).decode()

        # Create cache data with timestamp
        cache_data = {
            "username": username,
            "encrypted_password": encrypted_password,
            "timestamp": time.time(),  # Unix timestamp
        }

        # Write to cache file
        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        # Set restrictive permissions (owner read/write only)
        cache_path.chmod(0o600)

    except Exception:
        # Silently fail - caching is optional
        pass


def load_password_from_cache(username: str) -> Optional[str]:
    """Load and decrypt password from cache if not expired.

    Args:
        username: Username to load cached password for

    Returns:
        Decrypted password if cache valid and not expired, None otherwise
    """
    cache_path = Path.home() / ".cl_client_cache"

    if not cache_path.exists():
        return None

    try:
        # Read cache file
        with open(cache_path) as f:
            cache_data = json.load(f)

        # Verify username matches
        cached_username = cache_data.get("username")
        if cached_username != username:
            return None

        # Check expiration (6 hours = 21600 seconds)
        timestamp = cache_data.get("timestamp", 0)
        current_time = time.time()
        age_hours = (current_time - timestamp) / 3600

        if age_hours > 6:
            # Cache expired
            clear_password_cache()
            return None

        # Decrypt password
        encrypted_password = cache_data.get("encrypted_password")
        if not encrypted_password:
            return None

        key = _get_encryption_key(username)
        cipher = Fernet(key)
        password = cipher.decrypt(encrypted_password.encode()).decode()

        return password

    except (json.JSONDecodeError, InvalidToken, KeyError, Exception):
        # Cache corrupted or decryption failed - clear it
        clear_password_cache()
        return None


def clear_password_cache() -> None:
    """Clear the password cache file."""
    cache_path = Path.home() / ".cl_client_cache"
    if cache_path.exists():
        try:
            cache_path.unlink()
        except Exception:
            pass  # Silently fail


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
    envvar="CL_AUTH_URL",
    help="Auth service URL (can be set in config file)",
)
@click.option(
    "--compute-url",
    envvar="CL_COMPUTE_URL",
    help="Compute service URL (can be set in config file)",
)
@click.option(
    "--store-url",
    envvar="CL_STORE_URL",
    help="Store service URL (can be set in config file)",
)
@click.option(
    "--mqtt-url",
    envvar="CL_MQTT_URL",
    help="MQTT broker URL (can be set in config file, e.g., mqtt://mqtt.example.com:1883)",
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
    auth_url: Optional[str],
    compute_url: Optional[str],
    store_url: Optional[str],
    mqtt_url: Optional[str],
    no_auth: bool,
    output_json: bool,
):
    """CL Client CLI - Command-line interface for compute, store, and auth operations.

    Configuration priority (highest to lowest):
      1. Command-line options
      2. Environment variables
      3. Config file (~/.cl_client_config.ini)

    Examples:
      # Using config file (recommended - create ~/.cl_client_config.ini)
      cl-client admin user list

      # Using environment variables
      export CL_AUTH_URL=http://auth.example.com:8000
      export CL_COMPUTE_URL=http://compute.example.com:8002
      export CL_STORE_URL=http://store.example.com:8001
      export CL_MQTT_URL=mqtt://mqtt.example.com:1883
      cl-client store list

      # Using CLI flags
      cl-client --auth-url http://localhost:8010 \
        --compute-url http://localhost:8012 \
        --store-url http://localhost:8011 \
        --mqtt-url mqtt://localhost:1883 \
        store list
    """
    # Suppress Rich console output in JSON mode to ensure clean JSON stdout
    if output_json:
        global console
        console = Console(file=open(os.devnull, "w"))

    # Load config file
    config = load_config_file()

    # Priority: CLI flags > env vars > config file
    auth_url = auth_url or config.get("auth_url")
    compute_url = compute_url or config.get("compute_url")
    store_url = store_url or config.get("store_url")
    mqtt_url = mqtt_url or config.get("mqtt_url")
    username = username or config.get("username")

    # Try to load cached password if username provided but no password
    if username and not password and not no_auth:
        cached_password = load_password_from_cache(username)
        if cached_password:
            password = cached_password
            if not output_json:
                click.echo("Using cached password", err=True)

    # Store config in context for commands to access
    ctx.ensure_object(dict)
    ctx.obj["username"] = username
    ctx.obj["password"] = password
    ctx.obj["auth_url"] = auth_url
    ctx.obj["compute_url"] = compute_url
    ctx.obj["store_url"] = store_url
    ctx.obj["mqtt_url"] = mqtt_url
    ctx.obj["no_auth"] = no_auth
    ctx.obj["output_json"] = output_json

    # Only create ServerPref if we have all URLs
    if auth_url and compute_url and store_url and mqtt_url:
        ctx.obj["server_config"] = ServerPref(
            auth_url=auth_url,
            compute_url=compute_url,
            store_url=store_url,
            mqtt_url=mqtt_url,
        )
    else:
        ctx.obj["server_config"] = None


async def get_client(ctx: click.Context) -> ComputeClient:
    """Get ComputeClient based on CLI context (auth or no-auth mode).

    Returns:
        ComputeClient instance (caller must close it)
    """
    username = ctx.obj.get("username")
    password = ctx.obj.get("password")
    no_auth = ctx.obj.get("no_auth", False)
    server_config = ctx.obj.get("server_config")
    output_json = ctx.obj.get("output_json", False)

    # If --no-auth flag explicitly set, use no-auth mode
    if no_auth:
        return ComputeClient(
            base_url=server_config.compute_url,
            server_pref=server_config,
        )

    # If username provided but no password, prompt for it
    if username and not password:
        if output_json:
            # In JSON mode, fall back to no-auth silently
            return ComputeClient(
                base_url=server_config.compute_url,
                server_pref=server_config,
            )
        else:
            # Prompt for password interactively
            password = click.prompt("Password", hide_input=True, type=str)

    # If no credentials at all, use no-auth mode
    if not (username and password):
        return ComputeClient(
            base_url=server_config.compute_url,
            server_pref=server_config,
        )

    # With credentials: create session, login, return client
    session = SessionManager(server_pref=server_config)
    try:
        await session.login(username, password)
        # Cache password after successful authentication
        if username and password:
            save_password_to_cache(username, password)
        # Store session in context for cleanup
        ctx.obj["session"] = session
        return session.create_compute_client()
    except Exception as e:
        await session.close()
        # Clear cache on auth failure
        if username:
            clear_password_cache()
        output_error(ctx, f"Authentication failed: {e}")


async def get_session_manager(ctx: click.Context) -> SessionManager:
    """Get authenticated SessionManager for admin operations.

    Raises:
        SystemExit if authentication fails or no credentials provided
    """
    username = ctx.obj.get("username")
    password = ctx.obj.get("password")
    server_config = ctx.obj.get("server_config")
    output_json = ctx.obj.get("output_json", False)

    # Check if username is provided
    if not username:
        output_error(
            ctx,
            "Username required. Provide via --username flag or set in config file (~/.cl_client_config.ini)",
        )

    # If password not provided, prompt for it interactively
    if not password:
        if output_json:
            output_error(
                ctx,
                "Password required in JSON mode. Use --password flag or set CL_PASSWORD env var",
            )
        else:
            # Prompt for password interactively
            password = click.prompt("Password", hide_input=True, type=str)

    session = SessionManager(server_pref=server_config)
    try:
        await session.login(username, password)
        # Cache password after successful authentication
        if username and password:
            save_password_to_cache(username, password)
        return session
    except Exception as e:
        await session.close()
        # Clear cache on auth failure
        if username:
            clear_password_cache()
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
    output_json = ctx.obj.get("output_json", False)

    # If --no-auth flag explicitly set, use guest mode
    if no_auth:
        return StoreManager.guest(base_url=server_config.store_url)

    # If username provided but no password, prompt for it
    if username and not password:
        if output_json:
            # In JSON mode, fall back to guest mode silently
            return StoreManager.guest(base_url=server_config.store_url)
        else:
            # Prompt for password interactively
            password = click.prompt("Password", hide_input=True, type=str)

    # If no credentials at all, use guest mode
    if not (username and password):
        return StoreManager.guest(base_url=server_config.store_url)

    # With credentials: create session, login, return store manager
    session = SessionManager(server_pref=server_config)
    try:
        await session.login(username, password)
        # Cache password after successful authentication
        if username and password:
            save_password_to_cache(username, password)
        # Store session in context for cleanup
        ctx.obj["session"] = session
        return session.create_store_manager()
    except Exception as e:
        await session.close()
        # Clear cache on auth failure
        if username:
            clear_password_cache()
        output_error(ctx, f"Authentication failed: {e}")


# Clear Cache Command


@cli.command("clear-cache")
def clear_cache():
    """Clear cached password (removes ~/.cl_client_cache)."""
    clear_password_cache()
    click.echo("✓ Password cache cleared")


# Admin Commands


@cli.group("admin")
def admin():
    """Administration commands (user management)."""
    pass


@admin.command("login")
@click.option("--username", "-u", help="Username (uses config if not provided)")
@click.option("--password", "-p", help="Password (prompts if not provided)")
@click.pass_context
def admin_login(ctx: click.Context, username: Optional[str], password: Optional[str]):
    """Login and cache credentials for subsequent commands.

    Username and password are optional - they can be taken from:
    - CLI flags (highest priority)
    - Config file (~/.cl_client_config.ini)
    - Interactive prompt (for password only)

    Examples:
        cl-client admin login --username admin --password mypass
        cl-client admin login -u admin -p mypass
        cl-client admin login  # Uses username from config, prompts for password
        cl-client admin login -u admin  # Prompts for password
    """
    # Get username from context if not provided
    if not username:
        username = ctx.obj.get("username")
        if not username:
            output_error(
                ctx,
                "Username required. Provide via --username flag or set in config file.",
            )

    # Get password from context or prompt
    if not password:
        # Check if password already cached
        cached_password = load_password_from_cache(username)
        if cached_password:
            password = cached_password
            if not should_use_json(ctx):
                click.echo("Using cached password", err=True)
        else:
            # Prompt for password interactively
            password = click.prompt("Password", hide_input=True, type=str)

    async def run():
        # Get server config from context
        server_config = ctx.obj.get("server_config")
        if not server_config:
            output_error(
                ctx,
                "Server configuration required. Set URLs via config file, environment variables, or CLI flags.",
            )

        # Create session and attempt login
        session = SessionManager(server_pref=server_config)
        try:
            await session.login(username, password)
            # Cache password after successful authentication
            save_password_to_cache(username, password)

            # Output success
            success = SuccessResponse(
                message=f"Successfully logged in as '{username}'. Password cached for 6 hours."
            )
            output_sdk_result(ctx, success)
        except Exception as e:
            # Clear cache on auth failure
            clear_password_cache()
            output_error(ctx, f"Login failed: {e}")
        finally:
            await session.close()

    asyncio.run(run())


@admin.command("logout")
@click.pass_context
def admin_logout(ctx: click.Context):
    """Logout and clear cached credentials.

    Examples:
        cl-client admin logout
    """
    clear_password_cache()

    success = SuccessResponse(message="Logged out successfully. Password cache cleared.")
    output_sdk_result(ctx, success)


@admin.group("user")
def user():
    """User management commands (admin only)."""
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
        cl-client --username admin --password admin admin user create newuser pass123
        cl-client admin user create john doe123 --admin
        cl-client admin user create jane doe456 -p read:jobs -p write:jobs
    """
    from cl_client import UserCreateRequest

    # Validate permissions
    if permissions:
        is_valid, invalid_perms = validate_permissions(permissions)
        if not is_valid:
            output_error(
                ctx,
                f"Invalid permissions: {', '.join(invalid_perms)}. Use 'cl-client admin permissions list' to see allowed permissions.",
            )

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
        cl-client admin user update 2 --password newpass123
        cl-client admin user update 2 --admin
        cl-client admin user update 2 --inactive
        cl-client admin user update 2 -p read:jobs -p write:jobs
    """
    from cl_client import UserUpdateRequest

    # Validate permissions
    if permissions:
        is_valid, invalid_perms = validate_permissions(permissions)
        if not is_valid:
            output_error(
                ctx,
                f"Invalid permissions: {', '.join(invalid_perms)}. Use 'cl-client admin permissions list' to see allowed permissions.",
            )

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


@admin.group("permissions")
def permissions_group():
    """Permissions management commands."""
    pass


@permissions_group.command("list")
@click.pass_context
def permissions_list(ctx: click.Context):
    """List all allowed permissions.

    Examples:
        cl-client admin permissions list
        cl-client admin permissions list --json
    """
    # Create a simple model for permissions list
    class PermissionsList(BaseModel):
        permissions: list[str]
        count: int

    permissions_data = PermissionsList(
        permissions=ALLOWED_PERMISSIONS,
        count=len(ALLOWED_PERMISSIONS),
    )

    output_sdk_result(ctx, permissions_data)


@admin.group("store")
def admin_store():
    """Store admin operations."""
    pass


@admin_store.command("config")
@click.pass_context
def store_get_config(ctx: click.Context):
    """Get store configuration (admin only).

    Examples:
        cl-client admin store config
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            result = await manager.get_pref()

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


@admin_store.command("get-guest-mode")
@click.pass_context
def store_get_guest_mode(ctx: click.Context):
    """Get store guest mode configuration (admin only).

    Examples:
        cl-client admin store get-guest-mode
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            result = await manager.get_pref()

            if result.is_error or result.data is None:
                output_error(
                    ctx, str(result.error) if result.is_error else "No data returned"
                )

            # Create simple response with just guest_mode
            class GuestModeResponse(BaseModel):
                guest_mode: bool
                service: str = "store"

            guest_mode_data = GuestModeResponse(guest_mode=result.data.guest_mode)
            output_sdk_result(ctx, guest_mode_data)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@admin_store.command("set-guest-mode")
@click.argument("enabled", type=bool)
@click.pass_context
def store_set_guest_mode(ctx: click.Context, enabled: bool):
    """Enable or disable guest mode for store (admin only).

    Guest mode allows unauthenticated access to the store service.

    Examples:
        cl-client admin store set-guest-mode true
        cl-client admin store set-guest-mode false
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
                message=f"Store guest mode {'enabled' if enabled else 'disabled'}"
            )
            output_sdk_result(ctx, success)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@admin_store.command("audit-report")
@click.pass_context
def store_audit_report(ctx: click.Context):
    """Generate audit report of orphaned resources (admin only).

    Reports orphaned files, faces, vectors, and MQTT messages.

    Examples:
        cl-client admin store audit-report
        cl-client admin store audit-report --json
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            result = await manager.get_audit_report()

            if result.is_error or result.data is None:
                output_error(
                    ctx, str(result.error) if result.is_error else "No data returned"
                )

            # Output SDK AuditReport model directly
            output_sdk_result(ctx, result.data)
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@admin_store.command("clear-orphans")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def store_clear_orphans(ctx: click.Context, yes: bool):
    """Clear orphaned resources (admin only).

    Removes orphaned files, faces, vectors, and MQTT messages.

    Examples:
        cl-client admin store clear-orphans
        cl-client admin store clear-orphans --yes  # Skip confirmation
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            # Get audit report first for confirmation
            if not yes:
                audit_result = await manager.get_audit_report()
                if audit_result.is_error or audit_result.data is None:
                    output_error(
                        ctx,
                        str(audit_result.error)
                        if audit_result.is_error
                        else "No data returned",
                    )

                report = audit_result.data
                total_orphans = (
                    len(report.orphaned_files)
                    + len(report.orphaned_faces)
                    + len(report.orphaned_vectors)
                    + len(report.orphaned_mqtt_messages)
                )

                if total_orphans == 0:
                    success = SuccessResponse(message="No orphaned resources found")
                    output_sdk_result(ctx, success)
                    return

                click.confirm(
                    f"Are you sure you want to clear {total_orphans} orphaned resources?",
                    abort=True,
                )

            result = await manager.clear_orphans()

            if result.is_error or result.data is None:
                output_error(
                    ctx, str(result.error) if result.is_error else "No data returned"
                )

            # Output SDK CleanupReport model directly
            output_sdk_result(ctx, result.data)
        except click.Abort:
            output_error(ctx, "Cleanup cancelled")
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@admin.group("compute")
def admin_compute():
    """Compute admin operations."""
    pass


@admin_compute.command("capabilities")
@click.pass_context
def compute_capabilities(ctx: click.Context):
    """Show current worker capabilities and availability.

    Examples:
        cl-client admin compute capabilities
    """

    async def run():
        config = ctx.obj.get("server_config")
        if not config:
            output_error(ctx, "Server configuration not found in context.")
            return

        async with ComputeClient(server_pref=config) as client:
            try:
                response = await client.get_capabilities()
                output_sdk_result(ctx, response)
            except Exception as e:
                output_error(ctx, str(e))

    asyncio.run(run())


@admin_compute.command("get-guest-mode")
@click.pass_context
def compute_get_guest_mode(ctx: click.Context):
    """Get compute guest mode configuration (admin only).

    Examples:
        cl-client admin compute get-guest-mode
    """

    async def run():
        config = ctx.obj.get("server_config")
        if not config:
            output_error(ctx, "Server configuration not found in context.")
            return

        # Get session for auth
        session = await get_session_manager(ctx)
        try:
            import httpx

            # Call /admin/pref endpoint
            url = f"{config.compute_url}/admin/pref"
            headers = {"Authorization": f"Bearer {session.get_token()}"}

            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                # Create simple response
                class GuestModeResponse(BaseModel):
                    guest_mode: bool
                    service: str = "compute"

                guest_mode_data = GuestModeResponse(guest_mode=data["guest_mode"])
                output_sdk_result(ctx, guest_mode_data)

        except Exception as e:
            output_error(ctx, str(e))
        finally:
            await session.close()

    asyncio.run(run())


@admin_compute.command("set-guest-mode")
@click.argument("enabled", type=bool)
@click.pass_context
def compute_set_guest_mode(ctx: click.Context, enabled: bool):
    """Enable or disable guest mode for compute (admin only).

    Guest mode allows unauthenticated access to the compute service.

    Examples:
        cl-client admin compute set-guest-mode true
        cl-client admin compute set-guest-mode false
    """

    async def run():
        config = ctx.obj.get("server_config")
        if not config:
            output_error(ctx, "Server configuration not found in context.")
            return

        # Get session for auth
        session = await get_session_manager(ctx)
        try:
            client = session.create_compute_client()
            result = await client.update_guest_mode(guest_mode=enabled)

            if result:
                success = SuccessResponse(
                    message=f"Compute guest mode {'enabled' if enabled else 'disabled'}"
                )
                output_sdk_result(ctx, success)
            else:
                output_error(ctx, "Failed to update guest mode")

            await client.close()
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


@store.command("upload")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--label", help="Entity label/name (for single file)")
@click.option("--description", help="Entity description")
@click.option("--parent-id", type=int, help="Parent collection ID")
@click.option("--recursive", "-r", is_flag=True, help="Recursively upload all images in directory")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation for batch uploads")
@click.pass_context
def upload_entity(
    ctx: click.Context,
    path: Path,
    label: Optional[str],
    description: Optional[str],
    parent_id: Optional[int],
    recursive: bool,
    yes: bool,
):
    """Upload media file or directory to store.

    Examples:
        cl-client store upload photo.jpg --label "Beach Sunset"
        cl-client store upload photo.jpg --label "Vacation" --description "Summer 2024" --parent-id 5
        cl-client store upload photos/ --recursive --parent-id 5
        cl-client store upload photos/ -r --yes  # Skip confirmation
    """

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            # Check if path is directory
            if path.is_dir():
                if recursive:
                    # Find all images in directory
                    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic'}
                    image_files = [
                        f for f in path.rglob('*')
                        if f.is_file() and f.suffix.lower() in image_extensions
                    ]

                    if not image_files:
                        output_error(ctx, f"No image files found in {path}")

                    # Confirm batch upload
                    if not yes:
                        click.confirm(
                            f"Found {len(image_files)} image(s) to upload. Continue?",
                            abort=True,
                        )

                    # Upload each file
                    success_count = 0
                    output_json = ctx.obj.get("output_json", False)

                    for img_file in image_files:
                        try:
                            # Use relative path as label if not provided
                            file_label = str(img_file.relative_to(path))
                            result = await manager.create_entity(
                                label=file_label,
                                description=description,
                                is_collection=False,
                                parent_id=parent_id,
                                image_path=img_file,
                            )

                            if not result.is_error:
                                success_count += 1
                                if not output_json:
                                    click.echo(f"✓ Uploaded: {file_label}", err=True)
                            else:
                                if not output_json:
                                    click.echo(f"✗ Failed: {file_label} - {result.error}", err=True)

                        except Exception as e:
                            if not output_json:
                                click.echo(f"✗ Error: {img_file.name} - {e}", err=True)

                    # Output summary
                    success = SuccessResponse(
                        message=f"Uploaded {success_count}/{len(image_files)} images"
                    )
                    output_sdk_result(ctx, success)

                else:
                    output_error(ctx, f"{path} is a directory. Use --recursive to upload all images.")

            else:
                # Single file upload
                result = await manager.create_entity(
                    label=label or path.name,
                    description=description,
                    is_collection=False,
                    parent_id=parent_id,
                    image_path=path,
                )

                if result.is_error or result.data is None:
                    output_error(
                        ctx, str(result.error) if result.is_error else "No data returned"
                    )

                # Output SDK EntityResult model directly
                output_sdk_result(ctx, result.data)

        except click.Abort:
            output_error(ctx, "Upload cancelled")
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

    DEPRECATED: Use 'upload' command instead for file uploads.

    Examples:
        cl-client store create --label "My Photos" --collection
        cl-client store create --label "Beach Sunset" --file sunset.jpg
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






# Compute Commands


@cli.group("compute")
def compute():
    """Compute operations (media processing plugins)."""
    pass


# CLIP Embedding Commands


@compute.group("clip-embedding")
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


@compute.group("media-thumbnail")
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


@compute.group("hash")
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


@compute.group("exif")
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





# Image Conversion Commands


@compute.group("image-conversion")
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


@compute.group("dino-embedding")
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


# Face Detection Commands


@compute.group("face-detection")
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
    ctx: click.Context, image: Path, watch: bool, timeout: float, output: Optional[Path]
):
    """Detect faces in an image.

    Returns bounding boxes, confidence scores, landmarks, and cropped face images.

    Examples:
        cl-client compute face-detection detect photo.jpg
        cl-client compute face-detection detect photo.jpg --output faces/
        cl-client compute face-detection detect photo.jpg --watch
    """

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
                    console.print("[green]✓ Face detection completed[/green]")
                    print_job_result(ctx, final_job)

                    # Download face images if output specified
                    if output and final_job.task_output and "faces" in final_job.task_output:
                        output.mkdir(parents=True, exist_ok=True)
                        faces = final_job.task_output["faces"]
                        for i, face in enumerate(faces):
                            if "file_path" in face:
                                face_file = output / f"face_{i}.png"
                                await client.download_job_file(
                                    final_job.job_id, face["file_path"], face_file
                                )
                        console.print(
                            f"[green]✓ Downloaded {len(faces)} face(s) to {output}[/green]"
                        )

                elif final_job:
                    output_error(ctx, f"Failed: {final_job.error_message}")
            else:
                with console.status("[bold green]Processing..."):
                    job = await client.face_detection.detect(
                        image=image, wait=True, timeout=timeout
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(ctx, job)

                    if output and job.task_output and "faces" in job.task_output:
                        output.mkdir(parents=True, exist_ok=True)
                        faces = job.task_output["faces"]
                        for i, face in enumerate(faces):
                            if "file_path" in face:
                                face_file = output / f"face_{i}.png"
                                await client.download_job_file(
                                    job.job_id, face["file_path"], face_file
                                )
                        console.print(
                            f"[green]✓ Downloaded {len(faces)} face(s) to {output}[/green]"
                        )
                else:
                    output_error(ctx, f"Failed: {job.error_message}")

        finally:
            await client.close()
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


# Face Embedding Commands


@compute.group("face-embedding")
def face_embedding():
    """Face embedding operations."""
    pass


@face_embedding.command("embed")
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option("--watch", "-w", is_flag=True, help="Watch progress in real-time")
@click.option("--timeout", "-t", default=60.0, help="Timeout in seconds")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Download embeddings to this file",
)
@click.pass_context
def embed_faces(
    ctx: click.Context, image: Path, watch: bool, timeout: float, output: Optional[Path]
):
    """Generate face embeddings from an image.

    Returns 128-dimensional embeddings for each detected face.

    Examples:
        cl-client compute face-embedding embed photo.jpg
        cl-client compute face-embedding embed photo.jpg --output embeddings.npy
        cl-client compute face-embedding embed photo.jpg --watch
    """

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
                    console.print("[green]✓ Face embeddings generated[/green]")
                    print_job_result(ctx, final_job)

                    # Download if output specified
                    if output and final_job.params and "output_path" in final_job.params:
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
                        image=image, wait=True, timeout=timeout
                    )

                if job.status == "completed":
                    console.print("[green]✓ Completed[/green]")
                    print_job_result(ctx, job)

                    if output and job.params and "output_path" in job.params:
                        output_path = job.params["output_path"]
                        await client.download_job_file(job.job_id, str(output_path), output)
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


@compute.group("hls-streaming")
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


@store.group("face")
def face():
    """Manage faces in the store."""
    pass


@face.command("delete")
@click.argument("face_id", type=int)
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete_face(ctx: click.Context, face_id: int, yes: bool):
    """Delete a face from the database."""

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            if not yes:
                click.confirm(
                    f"Are you sure you want to delete face ID: {face_id}?",
                    abort=True,
                )

            result = await manager.delete_face(face_id)
            output_sdk_result(ctx, result)
        except click.Abort:
            output_error(ctx, "Deletion cancelled")
        except Exception as e:
            output_error(ctx, str(e))
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


@store.command("intelligence")
@click.argument("entity_id", type=int)
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Save output to file")
@click.pass_context
def get_intelligence(ctx: click.Context, entity_id: int, output: Optional[Path]):
    """Get intelligence data for an entity."""

    async def run():
        manager = await get_store_manager(ctx)
        await manager.__aenter__()
        try:
            result = await manager.get_entity_intelligence(entity_id)

            if result.is_error or result.data is None:
                output_error(
                    ctx, str(result.error) if result.is_error else "No intelligence data found"
                )

            output_sdk_result(ctx, result.data)

            if output:
                with open(output, "w") as f:
                    f.write(result.data.model_dump_json(indent=2))
                if not should_use_json(ctx):
                    click.echo(f"Saved to {output}", err=True)
        except Exception as e:
            output_error(ctx, str(e))
        finally:
            await manager.__aexit__(None, None, None)
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())


if __name__ == "__main__":
    cli()
