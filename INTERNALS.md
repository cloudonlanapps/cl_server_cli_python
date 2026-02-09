# CL Client CLI - Developer Documentation

Internal documentation for developers working on the CLI codebase.

## Package Structure

### Single-File Architecture

The CLI is intentionally kept as a single-file application for simplicity:

```
src/cl_client_cli/
├── __init__.py          # Minimal package init
├── main.py              # Entire CLI implementation (~2,100 lines)
└── py.typed             # Type checking marker
```

**Why single-file?**
- Easy to navigate and understand
- No module interdependencies to manage
- Simpler testing and debugging
- Fast development iteration

### Main Components in main.py

1. **Imports & Configuration** (lines 1-50)
   - Standard library imports
   - Click framework
   - Rich console for formatting
   - Cryptography for password caching
   - CL Client SDK imports

2. **Permissions Configuration** (lines ~40-70)
   - `ALLOWED_PERMISSIONS` - List of valid permissions
   - `validate_permissions()` - Validates permissions against allowed list

3. **Helper Functions** (lines 51-250)
   - `load_config_file()` - Load ~/.cl_client_config.ini
   - Password caching functions (encrypt/decrypt/clear)
   - Output formatters (`output_sdk_result`, `output_error`)
   - Client factory functions (`get_client`, `get_session_manager`, `get_store_manager`)

3. **CLI Definition** (lines 251-550)
   - Main `@click.group()` with global options
   - Context setup (URLs, auth, config loading)

4. **Command Groups** (lines 551+)
   - `clear-cache` - Clear password cache
   - `admin` - All administration commands
     - `admin login` - Login and cache credentials
     - `admin logout` - Logout and clear cache
     - `admin permissions` - Permissions management
     - `admin user` - User management (5 commands)
     - `admin store` - Store admin operations (4 commands)
     - `admin compute` - Compute admin operations (2 commands)
   - `store` - Store CRUD operations (12 commands)
   - `compute` - Compute operations (media processing plugins)
     - `compute clip-embedding` - CLIP plugin
     - `compute dino-embedding` - DINO plugin
     - `compute exif` - EXIF plugin
     - `compute hash` - Hashing plugin
     - `compute image-conversion` - Image conversion
     - `compute media-thumbnail` - Thumbnails
     - `compute hls-streaming` - HLS streaming

### Click-Based Command Hierarchy

```
cl-client (root)
├── clear-cache
├── admin
│   ├── login
│   ├── logout
│   ├── permissions
│   │   └── list
│   ├── user
│   │   ├── create
│   │   ├── list
│   │   ├── get
│   │   ├── update
│   │   └── delete
│   ├── store
│   │   ├── config
│   │   ├── get-guest-mode
│   │   ├── set-guest-mode
│   │   ├── audit-report
│   │   └── clear-orphans
│   └── compute
│       ├── capabilities
│       ├── get-guest-mode
│       └── set-guest-mode
├── store
│   ├── list
│   ├── upload (new - with directory support)
│   ├── create (deprecated - use upload)
│   ├── get
│   ├── update
│   ├── patch
│   ├── delete
│   ├── versions
│   ├── intelligence
│   └── face
│       └── delete
└── compute
    ├── clip-embedding
    │   └── embed
    ├── dino-embedding
    │   └── embed
    ├── face-detection
    │   └── detect
    ├── face-embedding
    │   └── embed
    ├── exif
    │   └── extract
    ├── hash
    │   └── compute
    ├── image-conversion
    │   └── convert
    ├── media-thumbnail
    │   └── generate
    └── hls-streaming
        └── generate-manifest
```

## Development

### Setup

```bash
# Navigate to CLI directory
cd apps/cli_python

# Install dependencies
uv sync

# Verify installation
uv run cl-client --help
```

### Running from Source

```bash
# Run CLI directly
uv run cl-client [command] [args]

# Run with debugger
uv run python -m pdb -m cl_client_cli.main [command] [args]

# Run specific command
uv run cl-client compute clip-embedding embed photo.jpg
```

### Code Quality

```bash
# Type checking
uv run basedpyright src/

# Linting
uv run ruff check src/

# Formatting
uv run ruff format src/

# All checks at once
uv run basedpyright src/ && uv run ruff check src/ && uv run pytest tests/
```

### Running Tests

```bash
# All tests
uv run pytest tests/

# With coverage
uv run pytest tests/ --cov=cl_client_cli --cov-report=html

# Specific test file
uv run pytest tests/test_cli.py -v

# Specific test
uv run pytest tests/test_cli.py::TestCLIPEmbedding::test_embed_polling_mode

# Skip integration tests
uv run pytest tests/ -m "not integration"

# Skip admin-only tests
uv run pytest tests/ -m "not admin_only"
```

### Adding Dependencies

Update `pyproject.toml`:

```toml
[project]
dependencies = [
    "cl-client @ git+https://github.com/cloudonlanapps/cl_server_sdk_python.git@main",
    "click>=8.1.0",
    "rich>=13.0.0",
    "cryptography>=41.0.0",
    # Add new dependency here
]
```

Then run:
```bash
uv sync
```

## Architecture

### Configuration Priority

The CLI uses a three-tier configuration system:

1. **CLI flags** (highest priority)
2. **Environment variables**
3. **Config file** (`~/.cl_client_config.ini`) (lowest priority)

Example:
```bash
# CLI flag wins
cl-client --auth-url http://custom:8010 store list

# Env var used if no flag
export CL_AUTH_URL=http://localhost:8010
cl-client store list

# Config file used if neither above
# ~/.cl_client_config.ini contains auth_url
cl-client store list
```

### Configuration File

Location: `~/.cl_client_config.ini`

Format:
```ini
[cl_client]
auth_url = http://localhost:8010
compute_url = http://localhost:8012
store_url = http://localhost:8011
mqtt_url = mqtt://localhost:1883
username = admin
# Note: password NOT stored for security
```

**Security**: Passwords are NEVER stored in the config file. They are cached separately using encryption.

### Password Caching

**Purpose**: Avoid re-entering password on every command

**Mechanism**:
1. User logs in with `--username` and `--password`
2. After successful authentication, password is encrypted and cached
3. Cache expires after 6 hours
4. Cache is automatically cleared on authentication failure

**Implementation**:

```python
# Encryption key derivation
def _get_encryption_key(username: str) -> bytes:
    """Generate key from username + machine UUID"""
    machine_id = str(uuid.getnode())
    key_material = f"{username}:{machine_id}".encode()
    key_hash = hashlib.sha256(key_material).digest()
    return base64.urlsafe_b64encode(key_hash)

# Save password
def save_password_to_cache(username: str, password: str) -> None:
    """Encrypt and save password with timestamp"""
    key = _get_encryption_key(username)
    cipher = Fernet(key)  # AES-256 symmetric encryption
    encrypted = cipher.encrypt(password.encode()).decode()
    cache_data = {
        "username": username,
        "encrypted_password": encrypted,
        "timestamp": time.time(),
    }
    with open(Path.home() / ".cl_client_cache", "w") as f:
        json.dump(cache_data, f)

# Load password
def load_password_from_cache(username: str) -> Optional[str]:
    """Decrypt and return password if not expired (6 hours)"""
    # Check expiration
    age_hours = (time.time() - cache_data["timestamp"]) / 3600
    if age_hours > 6:
        clear_password_cache()
        return None
    # Decrypt
    key = _get_encryption_key(username)
    cipher = Fernet(key)
    return cipher.decrypt(encrypted).decode()
```

**Security Features**:
- AES-256 encryption (via Fernet)
- Machine-specific encryption key (uses UUID)
- User-specific encryption (username in key)
- 6-hour expiration
- File permissions: 0o600 (owner read/write only)
- Auto-clear on authentication failure

**Manual clearing**:
```bash
cl-client clear-cache
```

### Authentication Flow

```
1. User runs command with credentials
   ↓
2. CLI checks for cached password
   ├─ Found & valid → Use cached password
   └─ Not found/expired → Use provided password
   ↓
3. Create SessionManager with credentials
   ↓
4. Call session.login()
   ├─ Success → Cache password, continue
   └─ Failure → Clear cache, exit with error
   ↓
5. Execute command
   ↓
6. Close session
```

### Permissions System

The CLI validates user permissions against an allowed list to prevent arbitrary permission assignment.

**Allowed Permissions List** (`ALLOWED_PERMISSIONS`):
```python
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
```

**Validation Function**:
```python
def validate_permissions(permissions: tuple[str, ...]) -> tuple[bool, list[str]]:
    """Validate permissions against allowed list.

    Returns:
        Tuple of (is_valid, list_of_invalid_permissions)
    """
    invalid = [p for p in permissions if p not in ALLOWED_PERMISSIONS]
    return (len(invalid) == 0, invalid)
```

**Usage in Commands**:
```python
# In user create/update commands
if permissions:
    is_valid, invalid_perms = validate_permissions(permissions)
    if not is_valid:
        output_error(
            ctx,
            f"Invalid permissions: {', '.join(invalid_perms)}. "
            "Use 'cl-client admin permissions list' to see allowed permissions.",
        )
```

**Updating Allowed Permissions**:

To add or modify permissions, update the `ALLOWED_PERMISSIONS` list in `main.py`:

```python
ALLOWED_PERMISSIONS = [
    # ... existing permissions ...
    "new:permission",  # Add new permission here
]
```

No other code changes needed - validation will automatically use the updated list.

### Client Factory Pattern

The CLI uses factory functions to create authenticated clients:

```python
async def get_client(ctx: click.Context) -> ComputeClient:
    """Get ComputeClient (auth or no-auth mode)"""
    if no_auth or not (username and password):
        return ComputeClient(base_url=compute_url, server_pref=config)

    session = SessionManager(server_pref=config)
    await session.login(username, password)
    save_password_to_cache(username, password)  # Cache on success
    return session.create_compute_client()

async def get_session_manager(ctx: click.Context) -> SessionManager:
    """Get SessionManager for admin operations"""
    session = SessionManager(server_pref=config)
    await session.login(username, password)
    save_password_to_cache(username, password)  # Cache on success
    return session

async def get_store_manager(ctx: click.Context):
    """Get StoreManager (auth or guest mode)"""
    if no_auth or not (username and password):
        return StoreManager.guest(base_url=store_url)

    session = SessionManager(server_pref=config)
    await session.login(username, password)
    save_password_to_cache(username, password)  # Cache on success
    return session.create_store_manager()
```

### Output Formatting

The CLI supports two output modes:

1. **Human-readable** (default)
   - Rich formatting with colors and tables
   - Progress bars for long operations
   - Friendly error messages

2. **JSON** (`--json` flag)
   - Machine-parseable output
   - Direct SDK model serialization
   - No extra formatting or colors

## Testing Strategy

### Test Organization

```
tests/
├── conftest.py              # Pytest fixtures
├── README.md                # Testing documentation
└── test_cli.py              # All CLI tests
```

### Test Categories

1. **Unit Tests** (29 tests)
   - Command invocation
   - Parameter validation
   - Output formatting
   - Error handling

2. **Integration Tests** (11 tests)
   - Marked with `@pytest.mark.integration`
   - Require real server connection
   - Test end-to-end workflows
   - Skip with: `pytest -m "not integration"`

3. **Admin Tests**
   - Marked with `@pytest.mark.admin_only`
   - Require admin credentials
   - Test user management and config
   - Skip with: `pytest -m "not admin_only"`

### Key Fixtures

```python
@pytest.fixture
def mock_compute_client():
    """Mock ComputeClient for testing"""
    return MagicMock(spec=ComputeClient)

@pytest.fixture
def temp_file(tmp_path):
    """Create temporary test file"""
    file_path = tmp_path / "test_image.jpg"
    file_path.write_bytes(b"fake image data")
    return file_path

@pytest.fixture
def completed_job():
    """Mock completed job response"""
    return Job(
        job_id="test-123",
        status="completed",
        task_type="clip_embedding",
        task_output={"embedding_dim": 512}
    )
```

### Mocking Patterns

```python
# Mock compute client
def test_clip_embed(mock_compute_client, temp_file, completed_job):
    mock_compute_client.clip_embedding.embed_image = AsyncMock(
        return_value=completed_job
    )

    with patch("cl_client_cli.main.get_client", return_value=mock_compute_client):
        runner = CliRunner()
        result = runner.invoke(cli, ["compute", "clip-embedding", "embed", str(temp_file)])
        assert result.exit_code == 0
```

### Coverage Requirements

- Minimum: 70% (enforced in pyproject.toml)
- Current: ~80%
- Goal: 85%+

Run coverage report:
```bash
uv run pytest tests/ --cov=cl_client_cli --cov-report=html
open htmlcov/index.html
```

## Adding New Commands

### Step 1: Determine Command Location

Choose the appropriate group:
- **Admin operations** → `admin` group
- **Store operations** → `store` group
- **Compute plugins** → `compute` group
- **Utility commands** → root `cli` group

### Step 2: Add Command

```python
@[group].command("command-name")
@click.argument("arg", type=str)
@click.option("--flag", is_flag=True, help="Description")
@click.pass_context
def my_command(ctx: click.Context, arg: str, flag: bool):
    """Command description.

    Examples:
        cl-client [group] command-name arg --flag
    """

    async def run():
        # Get authenticated client if needed
        client = await get_client(ctx)

        try:
            # Call SDK method
            result = await client.some_method(arg)

            # Handle result
            if result.is_error:
                output_error(ctx, str(result.error))

            # Output result
            output_sdk_result(ctx, result.data)

        finally:
            await client.close()
            session = ctx.obj.get("session")
            if session:
                await session.close()

    asyncio.run(run())
```

### Step 3: Add Tests

```python
def test_my_command(mock_compute_client, temp_file):
    """Test my_command with mock client."""
    # Setup mock
    mock_compute_client.some_method = AsyncMock(
        return_value=Result(data="success")
    )

    # Mock get_client
    with patch("cl_client_cli.main.get_client", return_value=mock_compute_client):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["group", "command-name", "arg", "--flag"]
        )

        # Assertions
        assert result.exit_code == 0
        assert "success" in result.output
        mock_compute_client.some_method.assert_called_once()
```

### Step 4: Update Documentation

Add to README.md:
```markdown
### My New Command

Description of what it does.

```bash
cl-client group command-name arg --flag
```
```

### Click Decorator Reference

Common decorators:

```python
# Command definition
@group.command("name")           # Add command to group

# Arguments (required, positional)
@click.argument("name", type=str)
@click.argument("id", type=int)
@click.argument("file", type=click.Path(exists=True, path_type=Path))

# Options (optional, named)
@click.option("--flag", is_flag=True, help="Boolean flag")
@click.option("--value", type=int, default=10, help="Integer value")
@click.option("--name", required=True, help="Required option")
@click.option("--multiple", "-m", multiple=True, help="Can specify multiple times")

# Context access
@click.pass_context                # Get ctx with config and auth

# Groups
@cli.group("name")                 # Create command group
@group.group("subgroup")           # Create nested group
```

## Common Development Tasks

### Add New Plugin Support

1. Add plugin group under `compute`:
```python
@compute.group("my-plugin")
def my_plugin():
    """My plugin description."""
    pass
```

2. Add plugin commands:
```python
@my_plugin.command("process")
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def process(ctx: click.Context, input: Path):
    async def run():
        client = await get_client(ctx)
        try:
            job = await client.my_plugin.process(input=input)
            output_sdk_result(ctx, job)
        finally:
            await client.close()
    asyncio.run(run())
```

3. Add tests for new plugin

### Change Command Structure

Reorganizing commands requires updating:
1. Command decorator (`@cli.command` → `@group.command`)
2. Tests (update command path in `runner.invoke()`)
3. README.md examples
4. User migration guide if breaking change

### Debug Authentication Issues

```bash
# Enable verbose output
uv run python -m pdb -m cl_client_cli.main --username admin --password admin store list

# Check cache
cat ~/.cl_client_cache

# Clear cache and retry
uv run cl-client clear-cache
uv run cl-client --username admin --password admin store list
```

### Profile Performance

```python
# Add timing decorator
import time
from functools import wraps

def timing(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await f(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{f.__name__} took {elapsed:.2f}s")
        return result
    return wrapper

# Use in commands
@timing
async def run():
    # command logic
    pass
```

## Troubleshooting

### Common Issues

**Issue**: Command not found
```bash
# Solution: Use uv run
uv run cl-client [command]
```

**Issue**: Import errors
```bash
# Solution: Reinstall dependencies
uv sync --reinstall
```

**Issue**: Authentication fails with cached password
```bash
# Solution: Clear cache
uv run cl-client clear-cache
```

**Issue**: Tests failing after code changes
```bash
# Solution: Update mock paths if functions moved
# Check import paths in test files
```

### Debug Mode

Add debug output to commands:

```python
def my_command(ctx: click.Context):
    # Print context for debugging
    if ctx.obj.get("debug"):
        click.echo(f"Context: {ctx.obj}", err=True)

    async def run():
        # Add logging
        click.echo(f"Running with config: {ctx.obj}", err=True)
```

## Contributing

### Code Style

- Follow PEP 8
- Use type hints
- Document functions with docstrings
- Add examples to command help text
- Keep functions focused and small

### Commit Messages

```
feat: add thumbnail generation command
fix: handle missing config file gracefully
docs: update INTERNALS.md with new architecture
test: add integration tests for store commands
refactor: extract client factory to helper function
```

### Pull Request Checklist

- [ ] Tests pass: `uv run pytest tests/`
- [ ] Type checking passes: `uv run basedpyright src/`
- [ ] Linting passes: `uv run ruff check src/`
- [ ] Coverage maintained: `--cov-fail-under=70`
- [ ] README.md updated with new commands
- [ ] INTERNALS.md updated if architecture changed
- [ ] Examples added to command help text

## Version History

- **0.1.0** - Initial release with 9 plugins, config file, password caching

## Support

- **User Documentation**: [README.md](README.md)
- **Testing Guide**: [tests/README.md](tests/README.md)
- **Library API**: [../README.md](../README.md)
