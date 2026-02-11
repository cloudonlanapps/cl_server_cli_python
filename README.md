# CL Client CLI Tool

Command-line interface for the CL Server compute service. Provides a user-friendly terminal interface to submit jobs, monitor progress, and download results.

**Package Manager:** uv
**Authentication Method:** None (uses cl-client library)
**Coverage:** 70% minimum

> **For Developers:** See [Integration with Library](#integration-with-library) section for programmatic access and library documentation.
>
> **For Testing:** See [tests/README.md](tests/README.md) for comprehensive testing guide, test organization, and coverage requirements.

## Features

- 🚀 **All 9 Plugins**: CLIP, DINO, EXIF, face detection/embedding, hashing, HLS streaming, image conversion, thumbnails
- 📊 **Real-time Progress**: MQTT-based live progress tracking with `--watch` flag
- 🎨 **Beautiful Output**: Rich terminal formatting with tables, progress bars, and colors
- 📥 **Automatic Downloads**: Download results with `--output` flag
- 🔄 **Two Modes**: Polling (default) and Watch (MQTT) workflows
- ⚡ **Fast & Efficient**: Built on the `cl-client` Python library

## Installation

### Prerequisites

- Python 3.12+
- `uv` package manager ([installation guide](https://github.com/astral-sh/uv))
- Running CL Server components (Auth, Compute, Store, MQTT)

### Install CLI Tool

**Individual Package Installation:**

```bash
# Navigate to CLI app directory
cd apps/cli_python

# Install dependencies (includes cl-client library)
uv sync

# Verify installation
uv run cl-client --help
```

## Quick Start

The CLI uses a login-once approach. Login with your credentials once, then use all commands without repeating credentials.

### Basic Usage

**Login first (one-time):**
```bash
# Login with all configuration
uv run cl-client login \
  --username admin \
  --password mypass \
  --auth-url http://localhost:8010 \
  --compute-url http://localhost:8012 \
  --store-url http://localhost:8011 \
  --mqtt-url mqtt://localhost:1883

# Or use short flags
uv run cl-client login -u admin -p mypass \
  --auth-url http://localhost:8010 \
  --compute-url http://localhost:8012 \
  --store-url http://localhost:8011 \
  --mqtt-url http://localhost:1883
```

**Then use commands (no credentials needed):**
```bash
# All commands use cached configuration
uv run cl-client store list
uv run cl-client compute clip-embedding embed photo.jpg
uv run cl-client admin user list
```

**With config file (recommended):**
```bash
# One-time setup: create config file
echo '{"server_pref": {
  "auth_url": "http://localhost:8010",
  "compute_url": "http://localhost:8012",
  "store_url": "http://localhost:8011",
  "mqtt_url": "mqtt://localhost:1883"
}}' > ~/.cl_client_config.json

# Login once (URLs loaded from config, prompt for credentials)
uv run cl-client login
Username: admin
Password: ****

# Use commands without repeating credentials
uv run cl-client store list
uv run cl-client compute clip-embedding embed photo.jpg
```

### Using Configuration File (Recommended)

```bash
# Set up config file once (JSON format)
cat > ~/.cl_client_config.json <<EOF
{
  "server_pref": {
    "auth_url": "http://localhost:8010",
    "compute_url": "http://localhost:8012",
    "store_url": "http://localhost:8011",
    "mqtt_url": "mqtt://localhost:1883"
  }
}
EOF

# Login once (reads URLs from config, prompts for credentials)
uv run cl-client login
Username: admin
Password: ****

# All subsequent commands use cached config
uv run cl-client store list
uv run cl-client compute clip-embedding embed photo.jpg
```

## Available Commands

All commands are now organized into logical groups:

### Session Management

**Login** (root-level command)
```bash
# Login with all credentials and URLs
uv run cl-client login --username admin --password mypass \
  --auth-url http://localhost:8010 \
  --compute-url http://localhost:8012 \
  --store-url http://localhost:8011 \
  --mqtt-url mqtt://localhost:1883

# Short form
uv run cl-client login -u admin -p mypass \
  --auth-url http://localhost:8010 \
  --compute-url http://localhost:8012 \
  --store-url http://localhost:8011

# Login using URLs from config file, prompt for credentials
uv run cl-client login
Username: admin
Password: ****

# Login with explicit username, prompt for password
uv run cl-client login -u admin
Password: ****

# After login, all commands use cached config (expires after 6 hours)
uv run cl-client admin user list
uv run cl-client store list
uv run cl-client compute clip-embedding embed photo.jpg
```

**Logout** (root-level command)
```bash
# Clear cached configuration and credentials
uv run cl-client logout
```

### 1. Admin Commands

#### Permissions Management

**List Available Permissions**
```bash
# See all allowed permissions
uv run cl-client admin permissions list

# JSON output
uv run cl-client admin permissions list --json
```

**Available Permissions (Placeholder - will be updated):**
- `read:jobs` - Read job information
- `write:jobs` - Create/modify jobs
- `delete:jobs` - Delete jobs
- `read:entities` - Read entities
- `write:entities` - Create/modify entities
- `delete:entities` - Delete entities
- `admin:users` - User management
- `admin:config` - Configuration management
- `admin:system` - System administration

#### User Management (Admin Only)

**Create User**
```bash
# Basic user
uv run cl-client admin user create <username> <password>

# Admin user
uv run cl-client admin user create <username> <password> --admin

# User with specific permissions (must be from allowed list)
uv run cl-client admin user create jane pass123 -p read:jobs -p write:jobs

# User with permissions and admin
uv run cl-client admin user create john pass456 --admin -p read:jobs -p write:jobs -p admin:users

# Note: Only permissions from the allowed list are accepted
# Use 'cl-client admin permissions list' to see available permissions
```

**List Users**
```bash
uv run cl-client admin user list
```

**Get User Details**
```bash
uv run cl-client admin user get <username>
```

**Update User**
```bash
# Update password
uv run cl-client admin user update <username> <new_password>

# Update and grant admin
uv run cl-client admin user update <username> <new_password> --admin

# Update with permissions
uv run cl-client admin user update john newpass --admin -p read:jobs -p write:jobs
```

**Delete User**
```bash
uv run cl-client admin user delete <username>
```

### 2. Store Management

#### Upload Media

**Upload Single File**
```bash
uv run cl-client store upload photo.jpg --label "Beach Sunset"
uv run cl-client store upload photo.jpg --label "Vacation" --description "Summer 2024" --parent-id 5
```

**Upload Directory** (with confirmation)
```bash
# Upload all images in directory recursively
uv run cl-client store upload photos/ --recursive --parent-id 5

# Skip confirmation
uv run cl-client store upload photos/ -r --yes
```

**Note**: The old `create` command still works for backward compatibility but `upload` is preferred.

#### CRUD Operations

#### Get Entity Intelligence
```bash
uv run cl-client store intelligence <entity_id>
```

#### Delete Face
```bash
uv run cl-client store face delete <face_id>
```

### 3. Admin Operations

#### Store Administration

**Get Store Configuration**
```bash
uv run cl-client admin store config
```

**Get/Set Store Guest Mode**
```bash
# Get current guest mode status
uv run cl-client admin store get-guest-mode

# Set guest mode
uv run cl-client admin store set-guest-mode true
uv run cl-client admin store set-guest-mode false
```

**Audit Report**
Generate a report of orphaned resources (files, faces, vectors, MQTT messages).
```bash
uv run cl-client admin store audit-report
uv run cl-client admin store audit-report --json
```

**Clear Orphans**
Clear orphaned resources with confirmation.
```bash
uv run cl-client admin store clear-orphans
uv run cl-client admin store clear-orphans --yes  # Skip confirmation
```

#### Compute Administration

**Get Worker Capabilities**
```bash
uv run cl-client admin compute capabilities
```

**Get/Set Compute Guest Mode**
```bash
# Get current guest mode status
uv run cl-client admin compute get-guest-mode

# Set guest mode
uv run cl-client admin compute set-guest-mode true
uv run cl-client admin compute set-guest-mode false
```

### 4. Compute Operations

All media processing plugins are under the `compute` group.

#### CLIP Embedding
```bash
uv run cl-client compute clip-embedding embed photo.jpg
uv run cl-client compute clip-embedding embed photo.jpg --output embedding.npy
uv run cl-client compute clip-embedding embed photo.jpg --watch
```

#### DINO Embedding
```bash
uv run cl-client compute dino-embedding embed photo.jpg
uv run cl-client compute dino-embedding embed photo.jpg --output embedding.npy
```

#### Face Detection
```bash
uv run cl-client compute face-detection detect photo.jpg
uv run cl-client compute face-detection detect photo.jpg --output faces/  # Downloads cropped faces
uv run cl-client compute face-detection detect photo.jpg --watch
```

Returns bounding boxes, confidence scores, facial landmarks, and cropped face images.

#### Face Embedding
```bash
uv run cl-client compute face-embedding embed photo.jpg
uv run cl-client compute face-embedding embed photo.jpg --output embeddings.npy
uv run cl-client compute face-embedding embed photo.jpg --watch
```

Returns 128-dimensional face embeddings for recognition and similarity matching.

#### EXIF Extraction
```bash
uv run cl-client compute exif extract photo.jpg
uv run cl-client compute exif extract photo.jpg --output metadata.json
```

#### Perceptual Hash
```bash
uv run cl-client compute hash compute photo.jpg
uv run cl-client compute hash compute photo.jpg --output hash.json
```

#### Image Conversion
```bash
uv run cl-client compute image-conversion convert input.png --format webp
uv run cl-client compute image-conversion convert input.jpg --format png --output result.png
```

#### Thumbnails
```bash
uv run cl-client compute media-thumbnail generate video.mp4
uv run cl-client compute media-thumbnail generate video.mp4 --width 320 --height 240
```

#### HLS Streaming
```bash
uv run cl-client compute hls-streaming generate-manifest video.mp4
uv run cl-client compute hls-streaming generate-manifest video.mp4 --segment-duration 10
```

### 5. Session Commands

**Login** (see Session Management section above)

**Logout**
```bash
# Clear cached configuration and credentials
uv run cl-client logout
```

## Configuration

The CLI uses a login-once approach with two configuration methods:

1. **Login command** (accepts all parameters: --auth-url, --compute-url, etc.)
2. **Configuration file** (`~/.cl_client_config.json` - optional, provides defaults for login)

### Configuration File (Optional)

Create `~/.cl_client_config.json` to avoid specifying URLs every time you login:

```json
{
  "server_pref": {
    "auth_url": "http://localhost:8010",
    "compute_url": "http://localhost:8012",
    "store_url": "http://localhost:8011",
    "mqtt_url": "mqtt://localhost:1883"
  }
}
```

**Note**: Credentials are never stored in the config file. They're provided during login and cached securely.

### Configuration Caching

After running `cl-client login`, your entire configuration is cached securely:

- **What's cached**: Full configuration (URLs, credentials, settings)
- **Encryption**: Fernet symmetric encryption (AES-128)
- **Expiration**: 6 hours
- **Storage**: `~/.cl_client_cache` (permissions: 0o600)
- **Machine-specific**: Encryption key derived from machine UUID
- **Auto-clear**: Cache cleared automatically on expiration or auth failure

**First login** (configuration cached):
```bash
cl-client login -u admin -p mypass --auth-url http://localhost:8010 --compute-url http://localhost:8012
✓ Logged in as admin
  Config cached at ~/.cl_client_cache
```

**Subsequent commands** (use cached config):
```bash
cl-client store list  # No credentials needed - uses cached config
cl-client compute clip-embedding embed photo.jpg
```

**Clear cache manually**:
```bash
cl-client logout
✓ Logged out successfully
  Cached config cleared
```

### Login Command Options

The `login` command accepts these options to configure your session:

- `--username, -u`: Username for authentication
- `--password, -p`: Password for authentication
- `--auth-url`: Auth service URL
- `--compute-url`: Compute service URL
- `--store-url`: Store service URL
- `--mqtt-url`: MQTT broker URL
- `--no-auth`: Use no-auth/guest mode (no credentials needed)
- `--json`: Output login result as JSON

**Note**: After login, all configuration is cached. You don't need to specify these options again until the cache expires (6 hours) or you logout.

### Command-Specific Options

Individual commands support specific flags:

- `--timeout SECONDS`: Maximum wait time for job completion (default: 30.0) - compute commands
- `--watch, -w`: Enable real-time MQTT progress tracking - compute commands
- `--output, -o FILE`: Automatically download result to specified file - compute commands
- `--json`: Output results in JSON format - all commands

## Output Formats

### Polling Mode Output

```
Submitting job...
✓ Job submitted: abc-123-def-456
Waiting for completion...
✓ Completed

Job ID: abc-123-def-456
Status: completed
Task Type: clip_embedding

Output:
╭───────────────┬────────╮
│ embedding_dim │    512 │
│ output_path   │ output │
╰───────────────┴────────╯
```

### Watch Mode Output

```
Submitting job...
✓ Job submitted: abc-123-def-456

Watching job progress...
Processing... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:02

✓ Completed

Job ID: abc-123-def-456
Status: completed
...
```

### Download Output

```
✓ Job submitted: abc-123-def-456
Waiting for completion...
✓ Completed
Downloading output/clip_embedding.npy...
✓ Downloaded to embedding.npy (2.1 KB)
```

## Error Handling

### Job Failures

```bash
$ uv run cl-client clip-embedding embed nonexistent.jpg
Error: File not found: nonexistent.jpg

$ uv run cl-client clip-embedding embed photo.jpg --timeout 1
Error: Job timeout after 1.0 seconds
```

### Server Connection Issues

```bash
$ uv run cl-client clip-embedding embed photo.jpg
Error: Could not connect to server at http://localhost:8002
Please ensure the compute server is running.
```

### Worker Unavailable

```bash
$ uv run cl-client clip-embedding embed photo.jpg
Error: No workers available with capability: clip_embedding
Please ensure workers are running.
```

## Testing

### Run CLI Tests

```bash
# Run all CLI tests
cd example
uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov=cl_client_cli --cov-report=html

# Run specific test file
uv run pytest tests/test_cli.py -v

# Run specific test
uv run pytest tests/test_cli.py::TestCLIPEmbedding::test_embed_polling_mode
```

### Test Coverage

Current test coverage: **80.48%** (21 tests)

**Test categories**:
- Command invocation tests (all 9 plugins)
- Polling mode tests
- Watch mode tests
- Parameter validation tests
- Error handling tests
- File download tests

### Test Requirements

Tests require:
- Mock compute client (provided by fixtures)
- Temporary test files (created automatically)
- No actual server connection needed

## Development

For developers working on the CLI codebase, see:
- **[INTERNALS.md](INTERNALS.md)** - Architecture, development setup, and adding new commands
- **[tests/README.md](tests/README.md)** - Testing guide

### Quick Developer Commands

```bash
# Install in development mode
uv sync

# Run all tests
uv run pytest tests/

# Type checking + linting
uv run basedpyright src/ && uv run ruff check src/
```

## Troubleshooting

### Command Not Found

```bash
# If cl-client command not found, use uv run:
uv run cl-client --help

# Or install globally:
uv pip install -e .
```

### Import Errors

```bash
# Ensure library is installed
cd ..
uv pip install -e .
cd example
uv sync
```

### Connection Refused

```bash
# Check server is running
curl http://localhost:8002/capabilities

# Check MQTT broker
telnet localhost 1883
```

### MQTT Progress Not Showing

```bash
# Verify MQTT broker is running
# Use --watch flag to enable MQTT mode
uv run cl-client clip-embedding embed photo.jpg --watch
```

## Migration Guide

### Latest Version (Login-Based Authentication)

**Major Changes**:
- **Login required**: Run `cl-client login` before using commands
- **No global flags**: `--username`, `--password`, `--auth-url`, etc. no longer accepted at root level
- **Config caching**: Entire configuration (not just password) cached after login
- **Login/logout moved**: `admin login` → `login`, `admin logout` → `logout`

| Old Usage | New Usage |
|-----------|-----------|
| `cl-client --username admin --password pass store list` | `cl-client login -u admin -p pass --auth-url ...`<br>`cl-client store list` |
| `cl-client admin login` | `cl-client login` |
| `cl-client admin logout` | `cl-client logout` |
| `cl-client --auth-url http://... store list` | Login once with URLs, then `cl-client store list` |

**Migration Steps**:
1. Remove all global flags from your scripts (`--username`, `--password`, `--auth-url`, etc.)
2. Run `cl-client login` once with all configuration
3. Use commands without credentials (they use cached config)
4. Optionally create `~/.cl_client_config.json` for login defaults

### Previous Version (Command Groups)

If you were using an older version with flat command structure, commands have been reorganized into logical groups:

| Old Command | New Command |
|-------------|-------------|
| `user create john pass` | `admin user create john pass` |
| `user list` | `admin user list` |
| `store admin config` | `admin store config` |
| `compute admin capabilities` | `admin compute capabilities` |
| `clip-embedding embed` | `compute clip-embedding embed` |
| `store list` | `store list` (unchanged) |

**Features Added**:
- Configuration file support (`~/.cl_client_config.json`)
- Secure config caching with Fernet encryption (6-hour expiration)
- Login/logout commands at root level
- Permissions validation and list command (`admin permissions list`)
- Enhanced store upload with directory support (`store upload photos/ --recursive`)
- Face detection and embedding commands

## Integration with Library

The CLI tool is built on top of the `cl-client` Python library. For programmatic access and advanced usage, see the library documentation:

- **Library API**: [../README.md](../README.md)
- **Developer Guide**: [../INTERNALS.md](../INTERNALS.md)
- **Library Tests**: [../tests/README.md](../tests/README.md)
- **CLI Internals**: [INTERNALS.md](INTERNALS.md)

### Using Library Directly

```python
from cl_client import ComputeClient
from pathlib import Path

async with ComputeClient() as client:
    # Same operations as CLI, but in Python
    job = await client.clip_embedding.embed_image(
        image=Path("photo.jpg"),
        wait=True
    )
    print(f"Embedding: {job.task_output['embedding']}")
```

## Support

- **Documentation**: See this file and library docs
- **Issues**: Report at project issue tracker
- **Library API**: [../README.md](../README.md)
- **Testing Guide**: [tests/README.md](tests/README.md)

## Version

- **CLI Version**: 0.1.0
- **Library Version**: 0.1.0 (cl-client)
- **Python**: 3.12+

## License

MIT License - see [../LICENSE](../LICENSE) file for details.
