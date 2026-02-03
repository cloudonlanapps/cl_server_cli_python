# Tests — CL Client CLI

Comprehensive guide to the test suite. For quick commands, see [QUICK.md](QUICK.md).

## Overview & Structure

The test suite is organized into two categories:

- **Unit tests** (`test_cli.py`, `conftest.py`) — Test the CLI commands with mocked dependencies. No external services required.
- **Integration tests** (`test_integration/`) — Test CLI commands against live servers (auth, compute, store).

## Test Organization

### Unit Tests

Run locally with no external dependencies:

```
test_cli.py                      # All CLI command tests (29 tests)
  TestStoreCommands              # Store commands (18 tests)
    - list, get, create, update, patch, delete entities
    - Admin commands: config, set-guest-mode
    - Version history
  TestNewDatabaseCommands        # Database features (11 tests)
    - store jobs: Job tracking for entities
    - faces: list, similar, download-embedding, matches
    - persons: list, get, update, faces
    - images: similar, download-embedding

conftest.py                      # Test fixtures and mocks
  - Mock SessionManager, StoreManager, StoreClient
  - Sample model fixtures (entities, faces, persons, etc.)
  - CLI runner fixtures
```

Run unit tests:

```bash
uv run pytest tests/test_cli.py -v
```

### Integration Tests (`test_integration/`)

Test the CLI against running servers. **Servers must be started first.**

```
test_database_features.py        # Database features integration (11 tests)
  TestJobTracking                # Job status tracking (1 test)
  TestFaceCommands               # Face detection & similarity (4 tests)
  TestPersonsCommands            # Person management (3 tests)
  TestImagesCommands             # CLIP similarity (3 tests)

conftest.py                      # Integration test fixtures
  - Pytest CLI options (--auth-url, --compute-url, --store-url)
  - SessionManager and StoreManager fixtures
  - Test media fixtures
  - Automatic cleanup fixtures

README.md                        # Integration test documentation
```

Run integration tests:

```bash
uv run pytest tests/test_integration/ \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin
```

---

## Test Details

### Unit Tests (29 tests)

#### Store Commands (18 tests)

**Entity CRUD:**
- `test_store_list` — List entities with pagination
- `test_store_get` — Get entity by ID
- `test_store_create` — Create entity with file upload
- `test_store_update` — Update entity metadata
- `test_store_patch` — Partial entity update
- `test_store_delete` — Delete entity

**Admin Operations:**
- `test_store_admin_config` — Get store configuration
- `test_store_admin_set_guest_mode` — Enable/disable guest mode

**Version History:**
- `test_store_versions` — List entity versions

#### Database Features (11 tests)

**Job Tracking:**
- `test_store_jobs` — Get entity job status

**Face Commands:**
- `test_faces_list` — List faces in entity
- `test_faces_similar` — Face similarity search
- `test_faces_download_embedding` — Download face embedding
- `test_faces_matches` — Face match history

**Person Commands:**
- `test_persons_list` — List known persons
- `test_persons_get` — Get person details
- `test_persons_update` — Update person name
- `test_persons_faces` — List person's faces

**Image Commands:**
- `test_images_similar` — CLIP similarity search
- `test_images_download_embedding` — Download CLIP embedding

### Integration Tests (11 tests)

Integration tests verify CLI commands against live services with real file uploads, background job processing, and database operations.

**Test Workflow:**
1. Upload test image (creates entity)
2. Wait for background jobs (face detection, embeddings)
3. Execute CLI command
4. Verify output and behavior
5. Automatic cleanup

**Features:**
- Smart polling for async operations (30 second timeout)
- Automatic cleanup of test entities (prefix: `test_`)
- Skip tests if services unavailable or jobs timeout
- Real background processing (face detection, CLIP embeddings)

See [test_integration/README.md](test_integration/README.md) for detailed documentation.

---

## Service Requirements

Integration tests require **running services**:

```
Auth Service:    http://localhost:8010
Store Service:   http://localhost:8011
Compute Service: http://localhost:8012
```

### Starting Servers

Refer to cl_server project (workspace) on how to launch servers/services.

### Compute Workers

Integration tests require compute workers with capabilities:
- `face_detection` — Face detection in images
- `face_embedding` — Face embeddings
- `clip_embedding` — CLIP vision embeddings

Workers are started as part of server launching process.

---

## Test Media

Integration tests require **test media files** (images with faces):

- `test_face_single.jpg` — Single face for face detection tests
- `test_face_multiple.jpg` — Multiple faces for face detection tests

**Location:** `TEST_VECTORS_DIR` environment variable (defaults to `~/cl_server_test_media`)

If media not found, integration tests skip with:
```
pytest.skip: Test image not found: /path/to/test_face_single.jpg
```

To use custom media location:

```bash
export TEST_VECTORS_DIR=/path/to/test/media
uv run pytest tests/test_integration/ ...
```

---

## Running Tests

### Quick Reference

See [QUICK.md](QUICK.md) for quick command reference.

### Unit Tests Only (Fast, No Servers)

```bash
uv run pytest tests/test_cli.py -v
```

**Duration:** ~0.3 seconds
**Coverage:** All CLI commands with mocked dependencies

### Integration Tests (Requires Servers)

Ensure servers are running first (see "Service Requirements" section above).

```bash
uv run pytest tests/test_integration/ \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin
```

**Duration:** ~3-5 minutes (depends on compute service)
**Coverage:** All database features with real services

### All Tests Together

```bash
# Run all unit tests first
uv run pytest tests/test_cli.py -v

# Then run integration tests
uv run pytest tests/test_integration/ \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin
```

### Run Specific Test

```bash
# Specific unit test
uv run pytest tests/test_cli.py::TestStoreCommands::test_store_list -v

# Specific integration test
uv run pytest tests/test_integration/test_database_features.py::TestFaceCommands::test_faces_list_command \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin
```

### Run Tests Matching Pattern

```bash
# All face-related tests
uv run pytest -k "face" -v

# All database feature tests (unit only)
uv run pytest tests/test_cli.py::TestNewDatabaseCommands -v
```

---

## Type Checking

The CLI codebase uses basedpyright for strict type checking.

Run type checker:

```bash
uv run basedpyright src/cl_client_cli/main.py
```

**Expected:** 0 errors

Type errors must be fixed (not ignored) unless unavoidable. The codebase maintains 100% type safety.

---

## Code Quality

### Test Fixtures

All test fixtures are defined in `conftest.py`:

**Mock Fixtures:**
- `mock_store_manager` — Mocked StoreManager with StoreClient
- `mock_session_manager` — Mocked SessionManager with AuthClient

**Sample Model Fixtures:**
- `sample_entity` — Entity with metadata
- `sample_entity_job` — Job status response
- `sample_face` — Face detection result
- `sample_known_person` — Known person record
- `sample_similar_faces_response` — Face similarity results
- `sample_similar_images_response` — CLIP similarity results

**CLI Fixtures:**
- `cli_runner` — CliRunner for testing Click commands
- `cli_env` — Environment variables for CLI

### Test Patterns

**Unit Test Pattern:**
```python
def test_command(mock_store_manager, sample_entity):
    # Setup mock
    mock_store_manager.method.return_value = StoreOperationResult(
        success="Operation successful",
        data=sample_entity
    )

    # Execute CLI command
    result = runner.invoke(cli, ["command", "args"])

    # Verify
    assert result.exit_code == 0
    assert "expected output" in result.output
    mock_store_manager.method.assert_called_once_with(...)
```

**Integration Test Pattern:**
```python
@pytest.mark.asyncio
async def test_command(cli_runner, cli_env, store_manager, test_image):
    # Create test entity
    result = await store_manager.create_entity(
        label="test_entity",
        image_path=test_image
    )
    entity_id = result.data.id

    # Wait for background processing
    await asyncio.sleep(5)

    # Execute CLI command
    cli_result = cli_runner.invoke(cli, ["command", str(entity_id)])

    # Verify
    assert cli_result.exit_code == 0
    assert "expected output" in cli_result.output
```

---

## Troubleshooting

### Unit Tests Fail: Import Errors

Ensure dependencies installed:

```bash
uv sync
```

### Integration Tests Fail: "Cannot connect to server"

Servers not running. Start them (see "Service Requirements" section).

### Integration Tests Fail: "Test image not found"

Test media directory not found. Set `TEST_VECTORS_DIR`:

```bash
export TEST_VECTORS_DIR=/path/to/test/media
```

### Integration Tests Skip: "Face detection did not complete in time"

Compute service may be overloaded or slow. Try:
1. Increasing wait times in test code
2. Running fewer tests in parallel
3. Checking compute service logs
4. Ensuring workers are running with required capabilities

### Type Errors

Run strict type checker:

```bash
uv run basedpyright src/cl_client_cli/main.py
```

Fix all errors (don't use `type: ignore` unless unavoidable).

---

## Test Statistics

**Total Tests:** 40
- **Unit Tests:** 29 (test_cli.py)
  - Store commands: 18 tests
  - Database features: 11 tests
- **Integration Tests:** 11 (test_integration/)
  - Job tracking: 1 test
  - Face commands: 4 tests
  - Person commands: 3 tests
  - Image commands: 3 tests

**Duration:**
- Unit tests: ~0.3 seconds
- Integration tests: ~3-5 minutes
- Total: ~5 minutes

**Type Safety:** 0 basedpyright errors (100% type safe)

---

## Documentation

- **QUICK.md** — Quick command reference
- **test_integration/README.md** — Integration test details
- **IMPLEMENTATION_SUMMARY.md** — Full implementation summary
- **PHASE_3_COMPLETE.md** — Phase 3 integration test details
