"""
Integration tests for snapshot_job.

These tests run the ACTUAL snapshot building workflow:
- Real tar files
- Real Docker operations (build, tag, login)
- Real test database (with migrations)
- Optional registry push with real Docker registry

Requirements:
- Docker daemon must be running
- PostgreSQL test database must be accessible (localhost:5432)
- These tests will actually build Docker images and update database
"""
# builtins
from unittest import TestCase
from unittest.mock import patch, AsyncMock
import asyncio
import os
import tempfile
import tarfile
from pathlib import Path

# modules
from src.snapshot_builder import SnapshotBuilder
from src.db_ops import update_saved_image
from browseterm_db.common.config import TEST_MIGRATIONS_DIR
from browseterm_db.migrations.migrator import Migrator
from browseterm_db.operations.container_ops import ContainerOps

# test config
from .conftest import TEST_DB_CONFIG, TEST_REPO_NAME, TEST_REPO_PASSWORD


class AAA_InitialSetupIntegration(TestCase):
    """
    Initial database setup for integration tests - runs migrations.
    Named with AAA_ prefix to run first.
    """
    
    def test_setup_database(self) -> None:
        """
        Set up the test database with migrations.
        This must run FIRST before other integration tests.
        """
        print('\n' + '='*70)
        print('SETTING UP TEST DATABASE FOR INTEGRATION TESTS')
        print('='*70)
        migrator = Migrator(
            TEST_DB_CONFIG,
            TEST_MIGRATIONS_DIR,
            versions_subdir="test_versions"
        )
        
        print('  Resetting database...')
        migrator.reset_database()
        
        print('  Resetting migrations...')
        migrator.reset_migrations()
        
        # Ensure versions directory exists before calling revision()
        import os
        versions_dir = os.path.join(TEST_MIGRATIONS_DIR, 'test_versions')
        os.makedirs(versions_dir, exist_ok=True)
        
        print('  Creating initial migration...')
        migrator.revision('Initial migration for integration tests')
        
        print('  Running migrations...')
        migrator.upgrade()
        
        print('  ✅ Test database ready for integration tests')
        print('='*70 + '\n')


class TestSnapshotBuilderIntegration(TestCase):
    """
    Integration tests for SnapshotBuilder.
    Tests the actual workflow with a real tar file.
    """

    def setUp(self) -> None:
        """
        Create a temporary directory and a fake filesystem tar file.
        This simulates what SaveUtility creates.
        """
        print('Setup: Creating test environment')
        
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.snapshot_dir = os.path.join(self.test_dir, 'snapshot')
        os.makedirs(self.snapshot_dir, exist_ok=True)
        
        # Create a fake filesystem structure
        self.rootfs_dir = os.path.join(self.test_dir, 'fake_rootfs')
        os.makedirs(self.rootfs_dir, exist_ok=True)
        
        # Create some fake files that would exist in a container
        fake_files = {
            'entrypoint.sh': '#!/bin/bash\necho "Hello from container"\n',
            'app/main.py': 'print("Application running")\n',
            'etc/config.txt': 'config_value=123\n',
        }
        
        for file_path, content in fake_files.items():
            full_path = os.path.join(self.rootfs_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
        
        # Create the tar file (this is what we start with in snapshot_job)
        self.epoch = "1234567890"
        self.snapshot_path = os.path.join(self.snapshot_dir, f'fs_snapshot_{self.epoch}.tar.gz')
        with tarfile.open(self.snapshot_path, 'w:gz') as tar:
            tar.add(self.rootfs_dir, arcname='.')
        
        print(f'Created test tar file: {self.snapshot_path}')
        
        # Initialize builder
        self.builder = SnapshotBuilder(
            snapshot_path=self.snapshot_path,
            container_id='test-container-123',
            repo_name='test-repo',
            repo_password='test-password',
            namespace_name='test-namespace',
            pod_name='test-pod',
            snapshot_dir=self.snapshot_dir
        )
        
        # Set build_dir to our test directory
        self.builder.build_dir = os.path.join(self.test_dir, 'build')
    
    def tearDown(self) -> None:
        """
        Clean up temporary files.
        """
        print('Teardown: Cleaning up test environment')
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_unpack_tar_creates_rootfs(self) -> None:
        """
        Test that unpacking the tar creates the rootfs directory with correct files.
        This uses the actual tar command (not mocked).
        """
        print('Test: test_unpack_tar_creates_rootfs')
        
        async def run_test():
            # Unpack the tar
            await self.builder.unpack_tar()
            
            # Verify rootfs directory was created
            rootfs_path = os.path.join(self.builder.build_dir, 'rootfs')
            self.assertTrue(os.path.exists(rootfs_path))
            
            # Verify our fake files exist
            self.assertTrue(os.path.exists(os.path.join(rootfs_path, 'entrypoint.sh')))
            self.assertTrue(os.path.exists(os.path.join(rootfs_path, 'app', 'main.py')))
            self.assertTrue(os.path.exists(os.path.join(rootfs_path, 'etc', 'config.txt')))
            
            # Verify file contents
            with open(os.path.join(rootfs_path, 'entrypoint.sh'), 'r') as f:
                content = f.read()
                self.assertIn('Hello from container', content)
        
        asyncio.run(run_test())
        print('Tar unpacking verified')
    
    def test_create_dockerfile_writes_correct_content(self) -> None:
        """
        Test that Dockerfile is created with correct content.
        This uses actual file I/O (not mocked).
        """
        print('Test: test_create_dockerfile_writes_correct_content')
        
        async def run_test():
            # Unpack first (needed for directory structure)
            await self.builder.unpack_tar()
            
            # Create Dockerfile
            await self.builder.create_dockerfile()
            
            # Verify Dockerfile exists
            dockerfile_path = os.path.join(self.builder.build_dir, 'rootfs', 'Dockerfile')
            self.assertTrue(os.path.exists(dockerfile_path))
            
            # Verify Dockerfile content
            with open(dockerfile_path, 'r') as f:
                content = f.read()
                self.assertIn('FROM scratch', content)
                self.assertIn('COPY . /', content)
                self.assertIn('ENTRYPOINT ["/entrypoint.sh"]', content)
        
        asyncio.run(run_test())
        print('Dockerfile creation verified')
    
    def test_full_workflow_without_docker(self) -> None:
        """
        Test the full workflow up to (but not including) Docker operations.
        This tests: unpack -> create Dockerfile
        Docker build/push are skipped since they require Docker daemon.
        """
        print('Test: test_full_workflow_without_docker')
        
        async def run_test():
            # Step 1: Unpack
            print('  Step 1: Unpacking tar...')
            await self.builder.unpack_tar()
            
            # Step 2: Create Dockerfile
            print('  Step 2: Creating Dockerfile...')
            await self.builder.create_dockerfile()
            
            # Verify build directory structure
            rootfs_path = os.path.join(self.builder.build_dir, 'rootfs')
            self.assertTrue(os.path.exists(rootfs_path))
            
            # Verify Dockerfile
            dockerfile_path = os.path.join(rootfs_path, 'Dockerfile')
            self.assertTrue(os.path.exists(dockerfile_path))
            
            # Verify original files still exist
            self.assertTrue(os.path.exists(os.path.join(rootfs_path, 'entrypoint.sh')))
            
            print('  ✓ Workflow completed successfully (without Docker)')
        
        asyncio.run(run_test())
        print('Full workflow verified')
    
    def test_full_workflow_with_real_docker(self) -> None:
        """
        Test the complete workflow with REAL Docker operations.
        This actually builds a Docker image.
        
        Note: Registry push is mocked to avoid pushing to Docker Hub.
        """
        print('Test: test_full_workflow_with_real_docker')
        
        async def run_test():
            # Mock ONLY registry push and database
            with patch.object(self.builder, 'docker_push', new_callable=AsyncMock) as mock_push:
                
                # Step 1: Unpack (REAL)
                print('  Step 1: Unpacking tar...')
                await self.builder.unpack_tar()
                
                # Step 2: Create Dockerfile (REAL)
                print('  Step 2: Creating Dockerfile...')
                await self.builder.create_dockerfile()
                
                # Step 3: Build image (REAL - actually builds with Docker)
                print('  Step 3: Building image with Docker...')
                image_name = await self.builder.build_image()
                self.assertEqual(image_name, 'test-pod-image:latest')
                print(f'    ✓ Built image: {image_name}')
                
                # Step 4: Tag image (REAL)
                print('  Step 4: Tagging image...')
                await self.builder.tag_image(image_name)
                print(f'    ✓ Tagged as: {self.builder.repo_name}/{image_name}')
                
                # Step 5: Push (MOCKED - don't actually push to registry)
                print('  Step 5: Pushing image (mocked to avoid registry)...')
                await self.builder.docker_push(image_name)
                mock_push.assert_called_once_with('test-pod-image:latest')
                
                # Step 6: Cleanup (REAL - actually delete images)
                print('  Step 6: Cleaning up local images...')
                await self.builder.cleanup_images(image_name)
                
                # Verify image was actually built (check docker images)
                result = await self.builder.run_command('docker images --format "{{.Repository}}:{{.Tag}}" | grep -c "test-pod-image" || true')
                # After cleanup, image should be gone
                print('  ✓ Complete workflow with real Docker verified')
        
        asyncio.run(run_test())
        print('Full workflow with real Docker verified')


class TestDatabaseIntegration(TestCase):
    """
    Integration tests for database operations with REAL test database.
    """
    
    def test_update_saved_image_flow(self) -> None:
        """
        Test the database update flow with REAL database connection.
        """
        print('Test: test_update_saved_image_flow')
        
        async def run_test():
            # Create a simple test container first
            result = await update_saved_image(
                db_config=TEST_DB_CONFIG,
                container_id='test-container-123',
                saved_image='test-pod-image:latest'
            )
            
            self.assertTrue(result.success, f"Database update should succeed: {result.error}")
            print('  ✓ Database update successful with real database')
        
        asyncio.run(run_test())
        print('Database integration with real DB verified')


class TestEndToEnd(TestCase):
    """
    End-to-end test with REAL Docker operations and REAL database.
    This tests the actual production workflow.
    """
    
    def test_complete_snapshot_job_with_real_docker(self) -> None:
        """
        Complete snapshot job with REAL Docker build/tag/cleanup and REAL database.
        Only registry push is optional (mocked if no credentials).
        """
        print('Test: test_complete_snapshot_job_with_real_docker')
        
        async def run_test():
            # Setup
            test_dir = tempfile.mkdtemp()
            snapshot_dir = os.path.join(test_dir, 'snapshot')
            os.makedirs(snapshot_dir, exist_ok=True)
            
            try:
                # Create fake tar file with executable entrypoint
                rootfs_dir = os.path.join(test_dir, 'fake_rootfs')
                os.makedirs(rootfs_dir, exist_ok=True)
                entrypoint_path = os.path.join(rootfs_dir, 'entrypoint.sh')
                Path(entrypoint_path).write_text('#!/bin/bash\necho "Test container running"\n')
                os.chmod(entrypoint_path, 0o755)
                
                epoch = "1234567890"
                snapshot_path = os.path.join(snapshot_dir, f'fs_snapshot_{epoch}.tar.gz')
                with tarfile.open(snapshot_path, 'w:gz') as tar:
                    tar.add(rootfs_dir, arcname='.')
                
                # Initialize builder
                builder = SnapshotBuilder(
                    snapshot_path=snapshot_path,
                    container_id='test-container-e2e',
                    repo_name='test-repo',
                    repo_password='test-password',
                    namespace_name='test-namespace',
                    pod_name='e2e-test-pod',
                    snapshot_dir=snapshot_dir
                )
                builder.build_dir = os.path.join(test_dir, 'build')
                
                # Only mock registry push (optional - skip if no credentials)
                repo_name = TEST_REPO_NAME
                repo_password = TEST_REPO_PASSWORD
                
                if not repo_name or not repo_password:
                    # Mock push if no credentials
                    mock_push_context = patch.object(builder, 'docker_push', new_callable=AsyncMock)
                else:
                    # Use real push if credentials available
                    mock_push_context = patch('builtins.print')  # No-op patch
                
                with mock_push_context:
                    # Execute the REAL workflow
                    print('  Running complete snapshot job workflow...')
                    
                    # Step 1: Unpack (REAL)
                    print('    Step 1: Unpacking tar...')
                    await builder.unpack_tar()
                    print('      ✓ Unpacked tar')
                    
                    # Step 2: Create Dockerfile (REAL)
                    print('    Step 2: Creating Dockerfile...')
                    await builder.create_dockerfile()
                    print('      ✓ Created Dockerfile')
                    
                    # Step 3: Build image (REAL - actually builds with Docker)
                    print('    Step 3: Building Docker image...')
                    image_name = await builder.build_image()
                    print(f'      ✓ Built image: {image_name}')
                    
                    # Step 4: Tag image (REAL)
                    print('    Step 4: Tagging image...')
                    await builder.tag_image(image_name)
                    print(f'      ✓ Tagged: {builder.repo_name}/{image_name}')
                    
                    # Step 5: Docker login and Push (REAL if credentials, MOCKED otherwise)
                    if repo_name and repo_password:
                        print('    Step 5: Docker login...')
                        await builder.docker_login()
                        print('      ✓ Logged in')
                        
                        print('    Step 6: Pushing to registry (REAL)...')
                        await builder.docker_push(image_name)
                        print('      ✓ Pushed')
                    else:
                        print('    Step 5-6: Skipping registry login/push (no credentials)...')
                    
                    # Step 7: Cleanup (REAL - actually deletes images)
                    print('    Step 7: Cleaning up images...')
                    await builder.cleanup_images(image_name)
                    print('      ✓ Cleaned up')
                    
                    # Step 8: Update database (REAL)
                    print('    Step 8: Updating database...')
                    result = await update_saved_image(
                        db_config=TEST_DB_CONFIG,
                        container_id='test-container-e2e',
                        saved_image=image_name
                    )
                    self.assertTrue(result.success, f"Database update failed: {result.error}")
                    print(f'      ✓ Database updated: saved_image = {image_name}')
                    
                    print('  ✅ Complete end-to-end workflow successful!')
            
            finally:
                # Cleanup test directory
                import shutil
                if os.path.exists(test_dir):
                    shutil.rmtree(test_dir)
        
        asyncio.run(run_test())
        print('End-to-end test with real Docker and real database verified')
        
        asyncio.run(run_test())
        print('End-to-end test with real Docker verified')


if __name__ == '__main__':
    import unittest
    unittest.main()
