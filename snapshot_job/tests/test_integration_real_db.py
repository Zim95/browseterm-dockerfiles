"""
Integration tests for snapshot_job with REAL test database and Docker registry.

These tests run the COMPLETE snapshot building workflow:
- Real tar files
- Real Docker operations (build, tag, push, cleanup)
- Real test database with migrations
- Real Docker registry (Docker Hub with test credentials)

Requirements:
- Docker daemon must be running
- PostgreSQL test database on localhost:5432
- REPO_NAME and REPO_PASSWORD environment variables (optional for push tests)
- These tests will actually push images to Docker registry
"""
# builtins
from unittest import TestCase
import asyncio
import os
import tempfile
import tarfile

# modules
from src.snapshot_builder import SnapshotBuilder
from browseterm_db.common.config import TEST_MIGRATIONS_DIR
from browseterm_db.migrations.migrator import Migrator
from browseterm_db.operations.container_ops import ContainerOps
from browseterm_db.operations.image_ops import ImageOps
from browseterm_db.operations.user_ops import UserOps
from browseterm_db.models.users import AuthProvider
from browseterm_db.models.containers import ContainerStatus
from browseterm_db.operations import OperationResult

# test config
from .conftest import TEST_DB_CONFIG, TEST_REPO_NAME, TEST_REPO_PASSWORD


class AAA_TestDatabaseSetup(TestCase):
    """
    Initial test database setup - runs migrations.
    Named with AAA_ prefix to run first.
    """
    
    def test_setup_database(self) -> None:
        """
        Set up the test database with migrations.
        This must run first to prepare the database.
        """
        print('\n' + '='*70)
        print('SETTING UP TEST DATABASE')
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
        
        breakpoint()
        print('  Creating initial migration...')
        migrator.revision('Initial migration for snapshot_job tests')
        
        print('  Running migrations...')
        migrator.upgrade()
        
        print('  ✅ Test database ready')
        print('='*70 + '\n')


class TestSnapshotJobWithRealDB(TestCase):
    """
    Integration tests for snapshot_job with REAL test database.
    Tests the complete workflow including database updates.
    """
    
    def setUp(self) -> None:
        """
        Set up test environment with:
        - Temporary directory and tar file
        - Real test database connection
        - Test user, image, and container
        """
        print('\n' + '-'*70)
        print('Setting up test environment...')
        
        # Database setup
        self.container_ops = ContainerOps(TEST_DB_CONFIG)
        self.image_ops = ImageOps(TEST_DB_CONFIG)
        self.user_ops = UserOps(TEST_DB_CONFIG)
        
        # Create test user
        user_data = {
            "email": f"snapshot-test-{os.urandom(4).hex()}@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": f"google_{os.urandom(4).hex()}",
            "name": "Snapshot Test User",
            "profile_picture_url": "https://example.com/profile.jpg",
            "is_active": True
        }
        user_result = self.user_ops.insert(user_data)
        assert user_result.success, f"Failed to create test user: {user_result.error}"
        self.user_id = user_result.data["id"]
        print(f'  Created test user: {self.user_id}')
        
        # Create test image
        image_data = {
            "name": f"snapshot-test-image-{os.urandom(4).hex()}",
            "image": "docker.io/library/python:3.11-slim",
            "is_active": True
        }
        image_result = self.image_ops.insert(image_data)
        assert image_result.success, f"Failed to create test image: {image_result.error}"
        self.image_id = image_result.data["id"]
        print(f'  Created test image: {self.image_id}')
        
        # Create test container
        self.container_name = f"snapshot-test-container-{os.urandom(4).hex()}"
        container_data = {
            "user_id": self.user_id,
            "image_id": self.image_id,
            "name": self.container_name,
            "status": ContainerStatus.RUNNING,
            "ip_address": "10.0.0.1"
        }
        container_result = self.container_ops.insert(container_data)
        assert container_result.success, f"Failed to create test container: {container_result.error}"
        self.container_id = container_result.data["id"]
        print(f'  Created test container: {self.container_id} ({self.container_name})')
        
        # Create temporary directory and fake filesystem tar
        self.test_dir = tempfile.mkdtemp()
        self.snapshot_dir = os.path.join(self.test_dir, 'snapshot')
        os.makedirs(self.snapshot_dir, exist_ok=True)
        
        # Create a fake filesystem structure
        self.rootfs_dir = os.path.join(self.test_dir, 'fake_rootfs')
        os.makedirs(self.rootfs_dir, exist_ok=True)
        
        # Create some fake files
        fake_files = {
            'entrypoint.sh': '#!/bin/bash\necho "Hello from snapshot test"\n',
            'app/main.py': 'print("Snapshot test application")\n',
        }
        
        for file_path, content in fake_files.items():
            full_path = os.path.join(self.rootfs_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
        
        # Create the tar file
        self.epoch = "1234567890"
        self.snapshot_path = os.path.join(self.snapshot_dir, f'fs_snapshot_{self.epoch}.tar.gz')
        with tarfile.open(self.snapshot_path, 'w:gz') as tar:
            tar.add(self.rootfs_dir, arcname='.')
        
        print(f'  Created snapshot tar: {self.snapshot_path}')
        
        # Get Docker registry credentials from test config
        self.repo_name = TEST_REPO_NAME
        self.repo_password = TEST_REPO_PASSWORD
        
        if not self.repo_name or not self.repo_password:
            print('  ⚠️  WARNING: REPO_NAME or REPO_PASSWORD not set - registry push will fail')
        
        # Initialize snapshot builder
        self.pod_name = f"snapshot-test-pod-{os.urandom(4).hex()}"
        self.namespace_name = "snapshot-test-ns"
        
        self.builder = SnapshotBuilder(
            snapshot_path=self.snapshot_path,
            container_id=self.container_id,
            repo_name=self.repo_name,
            repo_password=self.repo_password,
            namespace_name=self.namespace_name,
            pod_name=self.pod_name,
            snapshot_dir=self.snapshot_dir
        )
        
        self.builder.build_dir = os.path.join(self.test_dir, 'build')
        
        print('  ✅ Test environment ready')
        print('-'*70)
    
    def tearDown(self) -> None:
        """
        Clean up:
        - Temporary files
        - Database test data (optional - can leave for inspection)
        """
        print('\n' + '-'*70)
        print('Cleaning up test environment...')
        
        # Clean up temp files
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            print('  Removed temporary files')
        
        # Note: Not deleting database records so you can inspect them
        # Uncomment below to clean up database after each test:
        # if hasattr(self, 'container_id'):
        #     self.container_ops.delete({'id': self.container_id})
        # if hasattr(self, 'image_id'):
        #     self.image_ops.delete({'id': self.image_id})
        # if hasattr(self, 'user_id'):
        #     self.user_ops.delete({'id': self.user_id})
        
        print('  ℹ️  Database records preserved for inspection')
        print('-'*70 + '\n')
    
    def test_complete_snapshot_workflow_with_real_db(self) -> None:
        """
        Test the COMPLETE snapshot workflow:
        1. Unpack tar (REAL)
        2. Create Dockerfile (REAL)
        3. Build Docker image (REAL)
        4. Tag image (REAL)
        5. Login to registry (REAL)
        6. Push to registry (REAL)
        7. Update database (REAL)
        8. Cleanup local images (REAL)
        9. Verify database was updated correctly (REAL)
        """
        print('\n' + '='*70)
        print('TEST: Complete Snapshot Workflow with Real Database')
        print('='*70)
        
        async def run_workflow():
            # Step 1: Unpack tar
            print('\n  Step 1: Unpacking tar...')
            await self.builder.unpack_tar()
            print('    ✓ Unpacked')
            
            # Step 2: Create Dockerfile
            print('\n  Step 2: Creating Dockerfile...')
            await self.builder.create_dockerfile()
            print('    ✓ Created')
            
            # Step 3: Build Docker image
            print('\n  Step 3: Building Docker image...')
            image_name = await self.builder.build_image()
            print(f'    ✓ Built: {image_name}')
            
            # Step 4: Tag image
            print('\n  Step 4: Tagging image...')
            await self.builder.tag_image(image_name)
            tagged_name = self.builder.tagged_image_name
            print(f'    ✓ Tagged: {tagged_name}')
            
            # Step 5: Login to registry
            if self.repo_name and self.repo_password:
                print('\n  Step 5: Logging into Docker registry...')
                await self.builder.docker_login()
                print('    ✓ Logged in')
            else:
                print('\n  Step 5: Skipping registry login (no credentials)')
            
            # Step 6: Push to registry
            if self.repo_name and self.repo_password:
                print('\n  Step 6: Pushing image to registry...')
                await self.builder.docker_push(tagged_name)
                print(f'    ✓ Pushed to registry')
            else:
                print('\n  Step 6: Skipping registry push (no credentials)')
            
            # Step 7: Update database
            print('\n  Step 7: Updating database...')
            from src.db_ops import update_saved_image
            result = await update_saved_image(
                db_config=TEST_DB_CONFIG,
                container_id=self.container_id,
                saved_image_name=image_name
            )
            assert result.success, f"Database update failed: {result.error}"
            print(f'    ✓ Database updated: saved_image = {image_name}')
            
            # Step 8: Cleanup local images
            print('\n  Step 8: Cleaning up local Docker images...')
            await self.builder.cleanup_images(image_name)
            print('    ✓ Cleaned up')
            
            # Step 9: Verify database was updated
            print('\n  Step 9: Verifying database update...')
            container_result = self.container_ops.get({'id': self.container_id})
            assert container_result.success, "Failed to fetch container from database"
            
            container_data = container_result.data
            print(f'    Container ID: {container_data["id"]}')
            print(f'    Container name: {container_data["name"]}')
            print(f'    Saved image: {container_data.get("saved_image")}')
            print(f'    Status: {container_data["status"]}')
            
            assert container_data.get('saved_image') == image_name, \
                f"Expected saved_image '{image_name}', got '{container_data.get('saved_image')}'"
            
            print('    ✓ Database verification passed')
            
            return image_name, container_data
        
        # Run the async workflow
        image_name, container_data = asyncio.run(run_workflow())
        
        # Final assertions
        self.assertIsNotNone(image_name)
        self.assertEqual(container_data.get('saved_image'), image_name)
        self.assertEqual(container_data['id'], self.container_id)
        
        print('\n' + '='*70)
        print('✅ COMPLETE WORKFLOW TEST PASSED')
        print('='*70 + '\n')


class TestRegistryPush(TestCase):
    """
    Separate test for registry push functionality.
    Only runs if REPO_NAME and REPO_PASSWORD are set.
    """
    
    def setUp(self) -> None:
        """Check if registry credentials are available."""
        self.repo_name = TEST_REPO_NAME
        self.repo_password = TEST_REPO_PASSWORD
        
        if not self.repo_name or not self.repo_password:
            self.skipTest("Skipping registry push test - REPO_NAME or REPO_PASSWORD not set")
    
    def test_registry_push_with_real_credentials(self) -> None:
        """
        Test that we can actually push to Docker registry.
        This is a minimal test that creates a tiny image and pushes it.
        """
        print('\n' + '='*70)
        print('TEST: Registry Push with Real Credentials')
        print('='*70)
        
        async def test_push():
            # Create a minimal test image
            test_dir = tempfile.mkdtemp()
            try:
                # Create a minimal Dockerfile
                dockerfile_path = os.path.join(test_dir, 'Dockerfile')
                with open(dockerfile_path, 'w') as f:
                    f.write('FROM scratch\nCOPY test.txt /test.txt\n')
                
                # Create a test file
                test_file = os.path.join(test_dir, 'test.txt')
                with open(test_file, 'w') as f:
                    f.write('registry push test\n')
                
                # Initialize builder
                builder = SnapshotBuilder(
                    snapshot_path='/dev/null',  # Not used for this test
                    container_id='registry-test',
                    repo_name=self.repo_name,
                    repo_password=self.repo_password,
                    namespace_name='test',
                    pod_name='registry-test-pod',
                    snapshot_dir='/tmp'
                )
                
                # Build minimal image
                print('\n  Building minimal test image...')
                image_name = f"registry-push-test-{os.urandom(4).hex()}:latest"
                cmd = f"docker build -t {image_name} {test_dir}"
                await builder.run_command(cmd)
                print(f'    ✓ Built: {image_name}')
                
                # Tag for registry
                print('\n  Tagging for registry...')
                tagged_name = f"{self.repo_name}/{image_name}"
                await builder.run_command(f"docker tag {image_name} {tagged_name}")
                print(f'    ✓ Tagged: {tagged_name}')
                
                # Login
                print('\n  Logging into registry...')
                await builder.docker_login()
                print('    ✓ Logged in')
                
                # Push
                print('\n  Pushing to registry...')
                await builder.docker_push(tagged_name)
                print('    ✓ Pushed')
                
                # Cleanup
                print('\n  Cleaning up...')
                await builder.run_command(f"docker rmi {image_name} {tagged_name}")
                print('    ✓ Cleaned up')
                
            finally:
                import shutil
                shutil.rmtree(test_dir)
        
        asyncio.run(test_push())
        
        print('\n' + '='*70)
        print('✅ REGISTRY PUSH TEST PASSED')
        print('='*70 + '\n')


class ZZZ_Cleanup(TestCase):
    '''
    Cleanup: Delete all tables and reset migrations.
    Runs LAST (ZZZ_ prefix) after all tests complete.
    '''
    def test_cleanup(self) -> None:
        breakpoint()
        migrator = Migrator(TEST_DB_CONFIG, TEST_MIGRATIONS_DIR, versions_subdir="test_versions")
        migrator.reset_database()
        migrator.reset_migrations()