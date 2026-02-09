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

The CLI now requires server URLs to be provided either via command-line flags or environment variables.

### Basic Usage

**With command-line flags:**
```bash
# Submit job and wait for completion
uv run cl-client \
  --auth-url http://localhost:8010 \
  --compute-url http://localhost:8012 \
  --store-url http://localhost:8011 \
  --mqtt-url mqtt://localhost:1883 \
  compute clip-embedding embed photo.jpg
```

**With config file (recommended):**
```bash
# One-time setup
echo "[cl_client]
auth_url = http://localhost:8010
compute_url = http://localhost:8012
store_url = http://localhost:8011
mqtt_url = mqtt://localhost:1883
username = admin" > ~/.cl_client_config.ini

# Method 1: Use login command (recommended)
uv run cl-client admin login          # Uses username from config, prompts for password
# Or: uv run cl-client admin login -u admin -p mypass
uv run cl-client store list           # No credentials needed (uses cache)
uv run cl-client compute clip-embedding embed photo.jpg

# Method 2: First command caches password
uv run cl-client --password mypass store list  # First time (caches password)
uv run cl-client store list                    # Subsequent (uses cache)
```

### Using Configuration File (Recommended)

```bash
# Set up config file once
cat > ~/.cl_client_config.ini <<EOF
[cl_client]
auth_url = http://localhost:8010
compute_url = http://localhost:8012
store_url = http://localhost:8011
mqtt_url = mqtt://localhost:1883
username = admin
EOF

# First login (caches password)
uv run cl-client --password mypass store list

# Subsequent commands use config + cached password
uv run cl-client store list
uv run cl-client compute clip-embedding embed photo.jpg
```

## Available Commands

All commands are now organized into logical groups:

### 1. Admin Commands

#### Session Management

**Login**
```bash
# Login with explicit credentials
uv run cl-client admin login --username admin --password mypass
uv run cl-client admin login -u admin -p mypass

# Login using username from config file, prompt for password
uv run cl-client admin login
Password: ****

# Login with username from config, explicit password
uv run cl-client admin login --password mypass

# Login with explicit username, prompt for password
uv run cl-client admin login -u admin
Password: ****

# After login, subsequent commands don't need credentials (cached for 6 hours)
uv run cl-client admin user list
uv run cl-client store list
uv run cl-client compute clip-embedding embed photo.jpg
```

**Logout**
```bash
# Clear cached credentials
uv run cl-client admin logout
```

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

### 5. Utility Commands

#### Clear Password Cache
```bash
uv run cl-client clear-cache
```

## Configuration

The CLI supports three configuration methods with the following priority (highest to lowest):
1. **Command-line flags** (e.g., `--auth-url`)
2. **Environment variables** (e.g., `CL_AUTH_URL`)
3. **Configuration file** (`~/.cl_client_config.ini`)

### Configuration File (Recommended)

Create `~/.cl_client_config.ini` with your default settings:

```ini
[cl_client]
auth_url = http://localhost:8010
compute_url = http://localhost:8012
store_url = http://localhost:8011
mqtt_url = mqtt://localhost:1883
username = admin
# Note: password NOT stored for security - see Password Caching below
```

**Security Note**: Passwords are never stored in the config file. Use password caching (see below) for convenience.

**Copy example config**:
```bash
cp .cl_client_config.ini.example ~/.cl_client_config.ini
# Edit with your values
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `CL_AUTH_URL` | Auth service URL (e.g., http://localhost:8010) |
| `CL_COMPUTE_URL` | Compute service URL (e.g., http://localhost:8012) |
| `CL_STORE_URL` | Store service URL (e.g., http://localhost:8011) |
| `CL_MQTT_URL` | MQTT broker URL (e.g., mqtt://localhost:1883) |
| `CL_USERNAME` | Default username for authentication |
| `CL_PASSWORD` | Default password for authentication |

### Password Caching

For security and convenience, the CLI caches passwords after successful authentication:

- **Encryption**: AES-256 symmetric encryption
- **Expiration**: 6 hours
- **Storage**: `~/.cl_client_cache` (permissions: 0o600)
- **Machine-specific**: Encryption key derived from username + machine UUID
- **Auto-clear**: Cache cleared automatically on authentication failure

**First login** (password cached):
```bash
cl-client --username admin --password mypass store list
# Using cached password  # Shown on subsequent commands
```

**Subsequent commands** (uses cache):
```bash
cl-client store list  # No password needed - uses cached password
```

**Clear cache manually**:
```bash
cl-client clear-cache
```

### Global Options

All commands support these global flags:

- `--auth-url`: Auth service URL (overrides config file and env var)
- `--compute-url`: Compute service URL (overrides config file and env var)
- `--store-url`: Store service URL (overrides config file and env var)
- `--mqtt-url`: MQTT broker URL (overrides config file and env var)
- `--username`: Username for authenticated commands (overrides config file and env var)
- `--password`: Password for authenticated commands (cached after successful login)
- `--no-auth`: Disable authentication (if supported by server)
- `--json`: Output results in JSON format (**IMPORTANT**: Must be placed BEFORE the command, e.g., `cl-client --json admin user list`)
- `--timeout SECONDS`: Maximum wait time for job completion (default: 30.0)
- `--watch, -w`: Enable real-time MQTT progress tracking
- `--output, -o FILE`: Automatically download result to specified file

**Note on `--json` flag**: This is a global flag and must be placed immediately after `cl-client`:
```bash
# CORRECT
cl-client --json admin user list
cl-client --json store list

# WRONG (will not work)
cl-client admin user list --json
cl-client store list --json
```

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

If you were using an older version with flat command structure, commands have been reorganized into logical groups:

| Old Command | New Command |
|-------------|-------------|
| `user create john pass` | `admin user create john pass` |
| `user create john pass --admin` | `admin user create john pass --admin` |
| `user create john pass -p read:jobs` | `admin user create john pass -p read:jobs` |
| `user list` | `admin user list` |
| `user get 2` | `admin user get 2` |
| `user update 2 --password newpass` | `admin user update 2 --password newpass` |
| `user update 2 --admin -p read:jobs` | `admin user update 2 --admin -p read:jobs` |
| `user delete 2` | `admin user delete 2` |
| `store admin config` | `admin store config` |
| `store admin set-guest-mode` | `admin store set-guest-mode` |
| `store admin audit-report` | `admin store audit-report` |
| `store admin clear-orphans` | `admin store clear-orphans` |
| `compute admin capabilities` | `admin compute capabilities` |
| `clip-embedding embed` | `compute clip-embedding embed` |
| `dino-embedding embed` | `compute dino-embedding embed` |
| `exif extract` | `compute exif extract` |
| `hash compute` | `compute hash compute` |
| `image-conversion convert` | `compute image-conversion convert` |
| `media-thumbnail generate` | `compute media-thumbnail generate` |
| `hls-streaming generate-manifest` | `compute hls-streaming generate-manifest` |
| `store list` | `store list` (unchanged) |

**New features**:
- Configuration file support (`~/.cl_client_config.ini`)
- Secure password caching (6-hour expiration)
- Interactive password prompting (when username is in config but no cached password)
- Login/logout commands (`admin login`, `admin logout`)
- Permissions validation and list command (`admin permissions list`)
- Get guest mode commands (`admin store get-guest-mode`, `admin compute get-guest-mode`)
- Compute guest mode support (`admin compute set-guest-mode`)
- Face detection and face embedding commands (`compute face-detection detect`, `compute face-embedding embed`)
- Enhanced store upload with directory support (`store upload photos/ --recursive`)
- `clear-cache` command
- Consolidated admin commands under single `admin` group

**Command improvements**:
- `store create` → `store upload` (backward compatible, `create` still works)
- Directory upload with recursive scanning for images
- Batch upload confirmation dialogs

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
