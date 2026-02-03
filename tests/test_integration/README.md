# Integration Tests for CLI Database Features

These integration tests verify the CLI database commands (jobs, faces, persons, images) against real running services.

## Prerequisites

1. **Running Services**:
   - Auth service (default: http://localhost:8010)
   - Compute service (default: http://localhost:8012)
   - Store service (default: http://localhost:8011)

2. **Test Media**:
   - Test images with faces in `~/cl_server_test_media/images/`
   - Or set `TEST_VECTORS_DIR` environment variable to your test media location

3. **Admin Credentials**:
   - Username and password with admin privileges
   - Required for entity creation and cleanup

## Running the Tests

### Basic Usage

```bash
# Run all integration tests
pytest tests/test_integration/ \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin

# Run specific test class
pytest tests/test_integration/test_database_features.py::TestFaceCommands \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin

# Run specific test
pytest tests/test_integration/test_database_features.py::TestFaceCommands::test_faces_list_command \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin
```

### With Custom Test Media

```bash
TEST_VECTORS_DIR=/path/to/test/media pytest tests/test_integration/ \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin
```

### Verbose Output

```bash
pytest tests/test_integration/ -v -s \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin
```

## Test Coverage

### Job Tracking (`TestJobTracking`)
- ✅ `test_jobs_command_after_upload` - Verify job status tracking after entity upload

### Face Commands (`TestFaceCommands`)
- ✅ `test_faces_list_command` - List detected faces in an entity
- ✅ `test_faces_similar_command` - Find similar faces
- ✅ `test_faces_download_embedding` - Download face embedding as NPY
- ✅ `test_faces_matches_command` - View face match history

### Person Commands (`TestPersonsCommands`)
- ✅ `test_persons_list_command` - List all known persons
- ✅ `test_persons_get_update_commands` - Get person details and update name
- ✅ `test_persons_faces_command` - List faces for a person

### Image Commands (`TestImagesCommands`)
- ✅ `test_images_similar_command` - CLIP-based similarity search
- ✅ `test_images_similar_with_details` - Similarity search with entity details
- ✅ `test_images_download_embedding` - Download CLIP embedding as NPY

## Notes

### Test Timing
- Face detection typically completes in 5-10 seconds
- CLIP embedding generation may take 5-15 seconds
- Tests include appropriate wait times with timeouts

### Test Data Cleanup
- Tests automatically clean up entities with `test_` prefix
- Cleanup runs before and after each module

### Skipping Tests
- Tests will skip if services are not available
- Tests will skip if required test media is not found
- Some tests skip if background jobs don't complete in time

### Debugging

```bash
# Show CLI output for debugging
pytest tests/test_integration/ -v -s --tb=short \
    --auth-url=http://localhost:8010 \
    --compute-url=http://localhost:8012 \
    --store-url=http://localhost:8011 \
    --username=admin \
    --password=admin
```

## Expected Test Duration

- Full suite: ~3-5 minutes (depends on compute service processing time)
- Individual test: ~10-30 seconds

## Troubleshooting

### "Integration tests require --auth-url"
Ensure you're passing all required CLI arguments.

### "Test image not found"
Check that `TEST_VECTORS_DIR` points to valid test media directory.

### "Face detection did not complete in time"
The compute service may be overloaded or slow. Try:
1. Increasing wait times in test code
2. Running fewer tests in parallel
3. Checking compute service logs

### "Failed to create entity"
Check:
1. Store service is running
2. Credentials have write permissions
3. Test image file exists and is readable
