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

### Basic Usage (Polling Mode)

```bash
# Submit job and wait for completion
uv run cl-client \
  --auth-url http://localhost:8010 \
  --compute-url http://localhost:8012 \
  --store-url http://localhost:8011 \
  --mqtt-url mqtt://localhost:1883 \
  clip-embedding embed photo.jpg
```

### Using Environment Variables (Recommended)

```bash
export CL_AUTH_URL=http://localhost:8010
export CL_COMPUTE_URL=http://localhost:8012
export CL_STORE_URL=http://localhost:8011
export CL_MQTT_URL=mqtt://localhost:1883

# Now you can run commands without flags
uv run cl-client clip-embedding embed photo.jpg
```

## Available Commands

### 1-9. Traditional Plugin Commands
(CLIP, DINO, EXIF, Face Detection/Embedding, Hash, HLS, Image Conversion, Thumbnails)

All traditional plugin commands work as before, but with required URL configuration.

### 10. Store Management

#### Get Store Configuration (Admin Only)
```bash
uv run cl-client --username admin --password admin store admin config
```

#### Get Entity Intelligence
```bash
uv run cl-client store intelligence <entity_id>
```

#### Delete Face
```bash
uv run cl-client store face delete <face_id>
```

#### Audit Report (Admin Only)
Generate a report of orphaned resources (files, faces, vectors, MQTT messages).
```bash
uv run cl-client --username admin --password admin store admin audit-report
```

#### Clear Orphans (Admin Only)
Clear orphaned resources with confirmation.
```bash
uv run cl-client --username admin --password admin store admin clear-orphans
```

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `CL_AUTH_URL` | Auth service URL (e.g., http://localhost:8010) |
| `CL_COMPUTE_URL` | Compute service URL (e.g., http://localhost:8012) |
| `CL_STORE_URL` | Store service URL (e.g., http://localhost:8011) |
| `CL_MQTT_URL` | MQTT broker URL (e.g., mqtt://localhost:1883) |
| `CL_USERNAME` | Default username for authentication |
| `CL_PASSWORD` | Default password for authentication |

### Global Options

- `--auth-url`: Auth service URL
- `--compute-url`: Compute service URL
- `--store-url`: Store service URL
- `--mqtt-url`: MQTT broker URL
- `--username`: Username for authenticated commands
- `--password`: Password for authenticated commands
- `--no-auth`: Disable authentication (if supported by server)
- `--json`: Output results in JSON format
- `--timeout SECONDS`: Maximum wait time for job completion (default: 30.0)
- `--watch, -w`: Enable real-time MQTT progress tracking
- `--output, -o FILE`: Automatically download result to specified file

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

### Project Structure

```
example/
├── pyproject.toml          # CLI project configuration
├── README.md               # This file
├── src/
│   └── cl_client_cli/
│       ├── __init__.py
│       └── main.py         # CLI implementation
└── tests/
    ├── conftest.py         # Test fixtures
    ├── README.md           # Testing documentation
    └── test_cli.py         # CLI tests
```

### Development Setup

```bash
# Install in development mode
cd example
uv sync

# Run CLI from source
uv run cl-client --help

# Run with debugger
uv run python -m pdb -m cl_client_cli.main clip-embedding embed photo.jpg
```

### Adding a New Command

1. **Add command group** (if new plugin):
   ```python
   @cli.group()
   def my_plugin():
       """My plugin commands."""
       pass
   ```

2. **Add command**:
   ```python
   @my_plugin.command()
   @click.argument("input_file", type=click.Path(exists=True, path_type=Path))
   @common_options
   def process(input_file: Path, watch: bool, timeout: float, output: Optional[Path]):
       """Process input file."""
       async def run():
           async with ComputeClient() as client:
               job = await client.my_plugin.process(
                   input=input_file,
                   wait=not watch,
                   timeout=timeout
               )
               # Handle output...
       asyncio.run(run())
   ```

3. **Add tests** in `tests/test_cli.py`:
   ```python
   def test_my_plugin_process(self, mock_compute_client, temp_file, completed_job):
       mock_compute_client.my_plugin.process = AsyncMock(return_value=completed_job)
       runner = CliRunner()
       result = runner.invoke(cli, ["my-plugin", "process", str(temp_file)])
       assert result.exit_code == 0
   ```

### Code Quality

```bash
# Type checking
uv run basedpyright src/

# Linting
uv run ruff check src/

# Formatting
uv run ruff format src/

# All quality checks
uv run basedpyright src/ && uv run ruff check src/ && uv run pytest tests/
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

## Integration with Library

The CLI tool is built on top of the `cl-client` Python library. For programmatic access and advanced usage, see the library documentation:

- **Library API**: [../README.md](../README.md)
- **Developer Guide**: [../INTERNALS.md](../INTERNALS.md)
- **Library Tests**: [../tests/README.md](../tests/README.md)

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
