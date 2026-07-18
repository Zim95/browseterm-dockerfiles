# Snapshot Job Tests

This directory contains tests for the snapshot job module.

## Test Structure

### Unit Tests (Mocked)
These test individual components with all external dependencies mocked:

- **test_storage_retriever.py**: Tests storage layer abstraction (LOCAL vs MINIO)
- **test_snapshot_builder.py**: Tests individual SnapshotBuilder methods
- **test_db_ops.py**: Tests database update operations
- **test_config.py**: Tests configuration loading

### Integration Tests - Basic (Real Docker + Mocked DB/Registry)
Tests complete workflows with REAL Docker operations, minimal external dependencies:

- **test_integration.py**: Tests complete workflows starting from real tar files
  - Uses **real tar files** (created programmatically)
  - Uses **real Docker build/tag/cleanup** (requires Docker daemon running)
  - Mocks **ONLY**:
    - Database operations (no PostgreSQL required)
    - Registry push (no Docker Hub credentials required)

### Integration Tests - Full (Real Everything)
Tests COMPLETE production workflow with all real operations:

- **test_integration_real_db.py**: Full end-to-end test with real database and registry
  - Uses **real Docker** (build, tag, push, cleanup)
  - Uses **real test database** (with migrations)
  - Uses **real Docker registry** (pushes to Docker Hub if credentials provided)
  - Validates complete workflow including database updates

## Prerequisites

### For Unit Tests:
- No external dependencies (everything mocked)

### For Basic Integration Tests (test_integration.py):
- **Docker daemon must be running** (tests will actually build Docker images)
- Sufficient disk space for test images (~50MB per test run)

### For Full Integration Tests (test_integration_real_db.py):
- **Docker daemon must be running** (same as above)
- **PostgreSQL test database** with environment variables:
  ```bash
  TEST_DB_USERNAME=postgres
  TEST_DB_PASSWORD=postgres
  TEST_DB_HOST=localhost
  TEST_DB_PORT=5432
  TEST_DB_DATABASE=browseterm_test
  ```
- **Docker registry credentials** (optional, for push tests):
  ```bash
  REPO_NAME=your_dockerhub_username
  REPO_PASSWORD=your_dockerhub_token
  ```
  If not provided, registry push tests will be skipped

## Running Tests

### Run all unit tests (no Docker required):
```bash
poetry run python -m unittest tests.test_storage_retriever tests.test_snapshot_builder tests.test_db_ops tests.test_config -v
```

### Run basic integration tests (Docker required):
```bash
# Make sure Docker daemon is running first
docker ps

# Run all basic integration tests
poetry run python -m unittest tests.test_integration -v
```

### Run full integration tests (Docker + Database required):
```bash
# First time: Set up test database with migrations
poetry run python -m unittest tests.test_integration_real_db.AAA_TestDatabaseSetup -v

# Run all full integration tests
poetry run python -m unittest tests.test_integration_real_db -v

# Run specific test
poetry run python -m unittest tests.test_integration_real_db.TestSnapshotJobWithRealDB.test_complete_snapshot_workflow_with_real_db -v
```

### Run ALL tests:
```bash
poetry run python -m unittest discover tests/ -v
```

### Run a specific test:
```bash
poetry run python -m unittest tests.test_integration.TestSnapshotBuilderIntegration.test_full_workflow_with_real_docker -v
```

## What's Real vs Mocked

### Basic Integration Tests (test_integration.py)

**REAL Operations:**
✅ Tar file creation and unpacking  
✅ Dockerfile generation  
✅ Docker image build (actually builds with Docker daemon)  
✅ Docker image tag (actually tags images)  
✅ Docker image cleanup (actually removes images)  
✅ File system operations  
✅ Directory structure validation  

**Mocked Operations:**
🔧 Database updates (no PostgreSQL instance)  
🔧 Registry push (no Docker Hub pushes)

### Full Integration Tests (test_integration_real_db.py)

**REAL Operations:**
✅ All Docker operations (build, tag, push, cleanup)  
✅ PostgreSQL database with migrations  
✅ Database CRUD (create user, image, container)  
✅ Database updates (saved_image field)  
✅ Docker registry push (if credentials provided)  
✅ Complete end-to-end workflow validation  

**Mocked Operations:**
_None - everything is real!_

## Why This Approach?

### Basic Integration Tests Benefits:
1. **No Kubernetes cluster needed**: Tests start from tar files (the job's input)
2. **Uses REAL Docker**: Tests actually build/tag/cleanup images (validates real behavior)
3. **No database needed**: DB operations are mocked (reduces test dependencies)
4. **No registry needed**: Push is mocked (avoids Docker Hub rate limits)
5. **Fast and reliable**: Can run anywhere Docker is available

### Full Integration Tests Benefits:
1. **Tests complete production flow**: Exactly what runs in production
2. **Validates database integration**: Ensures saved_image updates work correctly
3. **Tests registry push**: Confirms Docker Hub authentication and upload work
4. **Detects integration issues**: Finds problems unit tests might miss
5. **Provides confidence**: If these pass, production should work

## Test Flow Simulation

### Basic Integration Tests Flow:
```
1. Create fake filesystem → tar it (test setup)
2. Unpack tar (REAL) → creates rootfs directory
3. Create Dockerfile (REAL) → writes to filesystem
4. Build image (REAL) → actually builds Docker image
5. Tag image (REAL) → actually tags the image
6. Push image (MOCKED) → simulates registry push
7. Cleanup (REAL) → actually removes local images
8. Update database (MOCKED) → simulates DB update
```

### Full Integration Tests Flow:
```
1. Set up test database (REAL migrations)
2. Create test user/image/container (REAL DB inserts)
3. Create fake filesystem → tar it (test setup)
4. Unpack tar (REAL)
5. Create Dockerfile (REAL)
6. Build image (REAL Docker build)
7. Tag image (REAL Docker tag)
8. Login to registry (REAL Docker login)
9. Push to registry (REAL Docker push - if credentials provided)
10. Update database (REAL DB update)
11. Cleanup images (REAL Docker rmi)
12. Verify database (REAL DB query)
13. Inspect records (preserved for manual verification)
```

## Debugging Tips

### If Docker build fails:
1. Check Docker daemon is running: `docker ps`
2. Check disk space: `docker system df`
3. Clean up old images: `docker image prune -a`

### If database tests fail:
1. Verify PostgreSQL is running: `psql -U postgres -h localhost -c '\l'`
2. Check environment variables are set correctly
3. Ensure test database exists (migrations will create schema)
4. Check database logs for connection issues

### If registry push fails:
1. Verify Docker Hub credentials: `docker login -u $REPO_NAME`
2. Check network connectivity
3. Verify repository exists (or you have permission to create it)
4. Check Docker Hub rate limits

## Inspecting Test Results

### View Docker images created by tests:
```bash
docker images | grep -E "test-pod-image|e2e-test|registry-push-test"
```

### View test database records:
```bash
# Connect to test database
psql -U $TEST_DB_USERNAME -h $TEST_DB_HOST -d $TEST_DB_DATABASE

# View containers created by tests
SELECT id, name, saved_image, status FROM containers WHERE name LIKE 'snapshot-test%';

# View users created by tests
SELECT id, email, name FROM users WHERE email LIKE 'snapshot-test%';
```

### Clean up test data:
```bash
# Remove Docker images
docker images | grep -E "test-pod-image|e2e-test" | awk '{print $3}' | xargs docker rmi -f

# Clean test database (from psql)
DELETE FROM containers WHERE name LIKE 'snapshot-test%';
DELETE FROM users WHERE email LIKE 'snapshot-test%';
```
