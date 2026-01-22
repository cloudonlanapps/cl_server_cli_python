# QUICK – Test Commands

## Run all unit tests

```bash
uv run pytest tests/test_cli.py -v
```

Duration: ~0.3 seconds
No external services required
All CLI commands tested with mocks

## Run all tests

```bash
# Run unit tests first
uv run pytest tests/test_cli.py -v

# Then run integration tests (requires servers)
uv run pytest tests/test_integration/ \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin
```

Duration: ~5 minutes total
Coverage: 70% minimum required
Servers must be started first: Auth (8010), Store (8011), Compute (8012)

## Run all integration tests

```bash
uv run pytest tests/test_integration/ \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin
```

Duration: ~3-5 minutes
Servers must be started first: Auth (8010), Store (8011), Compute (8012)
Requires test media in TEST_VECTORS_DIR
