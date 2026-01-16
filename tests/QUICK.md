# QUICK – Test Commands

## Run all unit tests (fast, no servers required)

```bash
uv run pytest tests/test_cli.py -v
```

- Duration: ~0.3 seconds
- No external services required
- All CLI commands tested with mocks

## Run all integration tests (requires servers)

```bash
uv run pytest tests/test_integration/ \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin
```

- Duration: ~3-5 minutes
- Servers must be started before triggering this test
- Tests against live services

## Run specific test class

```bash
# Unit test class
uv run pytest tests/test_cli.py::TestStoreCommands -v
uv run pytest tests/test_cli.py::TestNewDatabaseCommands -v

# Integration test class
uv run pytest tests/test_integration/test_database_features.py::TestFaceCommands \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin
```

## Run specific test

```bash
# Unit test
uv run pytest tests/test_cli.py::TestStoreCommands::test_store_list -v

# Integration test
uv run pytest tests/test_integration/test_database_features.py::TestFaceCommands::test_faces_list_command \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin
```

## Run tests matching pattern

```bash
# All face-related tests
uv run pytest -k "face" -v

# All person-related tests
uv run pytest -k "person" -v

# All image-related tests
uv run pytest -k "image" -v
```

## Type checking

```bash
uv run basedpyright src/cl_client_cli/main.py
```

- Expected: 0 errors

## Integration test with custom test media

```bash
TEST_VECTORS_DIR=/path/to/test/media uv run pytest tests/test_integration/ \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin
```

## Verbose output for debugging

```bash
uv run pytest tests/test_integration/ -v -s --tb=short \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin
```

## Collect all tests (no execution)

```bash
uv run pytest --collect-only -q
```
