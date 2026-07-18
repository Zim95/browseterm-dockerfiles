"""
Test the snapshot builder module.
"""
# builtins
from unittest import TestCase
from unittest.mock import Mock, patch, AsyncMock
import asyncio

# modules
from src.snapshot_builder import SnapshotBuilder


class TestSnapshotBuilder(TestCase):
    """
    Test SnapshotBuilder class.
    Verifies the complete snapshot building workflow.
    """

    def setUp(self) -> None:
        self.epoch = "1234567890"
        self.builder = SnapshotBuilder(
            snapshot_path=f"/mnt/snapshot/test-namespace/test-pod/fs_snapshot_{self.epoch}.tar.gz",
            container_id="test-container-123",
            repo_name="test-repo",
            repo_password="test-password",
            namespace_name="test-namespace",
            pod_name="test-pod",
            snapshot_dir="/mnt/snapshot"
        )

    def test_builder_initialization(self) -> None:
        """
        Test that SnapshotBuilder initializes correctly.
        """
        print('Test: test_builder_initialization')
        self.assertEqual(self.builder.container_id, "test-container-123")
        self.assertEqual(self.builder.repo_name, "test-repo")
        self.assertEqual(self.builder.pod_name, "test-pod")
        self.assertEqual(self.builder.namespace_name, "test-namespace")
        self.assertTrue(self.builder.build_dir.endswith("/test-namespace/test-pod/build"))
        print('Builder initialized correctly.')

    @patch('src.snapshot_builder.asyncio.create_subprocess_shell')
    def test_run_command_success(self) -> None:
        """
        Test successful command execution.
        """
        print('Test: test_run_command_success')
        
        async def run_test():
            # Mock successful process
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b'command output', None)
            mock_process.returncode = 0
            
            with patch('src.snapshot_builder.asyncio.create_subprocess_shell', return_value=mock_process):
                result = await self.builder.run_command('ls -l')
                self.assertEqual(result, 'command output')
        
        asyncio.run(run_test())
        print('Command executed successfully.')

    @patch('src.snapshot_builder.asyncio.create_subprocess_shell')
    def test_run_command_failure(self) -> None:
        """
        Test command execution failure.
        """
        print('Test: test_run_command_failure')
        
        async def run_test():
            # Mock failed process
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b'error output', None)
            mock_process.returncode = 1
            
            with patch('src.snapshot_builder.asyncio.create_subprocess_shell', return_value=mock_process):
                with self.assertRaises(Exception) as context:
                    await self.builder.run_command('failing-command')
                self.assertIn('Command failed with return code 1', str(context.exception))
        
        asyncio.run(run_test())
        print('Command failure handled correctly.')

    def test_unpack_tar(self) -> None:
        """
        Test tar unpacking.
        """
        print('Test: test_unpack_tar')
        
        async def run_test():
            with patch.object(self.builder, 'run_command', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = "unpacked"
                await self.builder.unpack_tar()
                
                # Verify command was called with correct arguments
                call_args = mock_run.call_args[0][0]
                self.assertIn('mkdir -p', call_args)
                self.assertIn('tar -xzf', call_args)
                self.assertIn(self.builder.snapshot_path, call_args)
        
        asyncio.run(run_test())
        print('Tar unpacking tested.')

    def test_create_dockerfile(self) -> None:
        """
        Test Dockerfile creation.
        """
        print('Test: test_create_dockerfile')
        
        async def run_test():
            with patch('builtins.open', create=True) as mock_open:
                await self.builder.create_dockerfile()
                
                # Verify file was opened for writing
                mock_open.assert_called_once()
                
                # Verify Dockerfile content
                handle = mock_open.return_value.__enter__.return_value
                written_content = ''.join([call[0][0] for call in handle.write.call_args_list])
                self.assertIn('FROM scratch', written_content)
                self.assertIn('COPY . /', written_content)
                self.assertIn('ENTRYPOINT', written_content)
        
        asyncio.run(run_test())
        print('Dockerfile creation tested.')

    def test_build_image_success(self) -> None:
        """
        Test successful image build.
        """
        print('Test: test_build_image_success')
        
        async def run_test():
            with patch.object(self.builder, 'run_command', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = "Successfully built abc123\nSuccessfully tagged test-pod-image:latest"
                
                image_name = await self.builder.build_image()
                
                self.assertEqual(image_name, "test-pod-image:latest")
                self.assertIn('docker image build', mock_run.call_args[0][0])
        
        asyncio.run(run_test())
        print('Image build tested.')

    def test_build_image_retry(self) -> None:
        """
        Test image build retry logic.
        """
        print('Test: test_build_image_retry')
        
        async def run_test():
            with patch.object(self.builder, 'run_command', new_callable=AsyncMock) as mock_run:
                # Fail twice, succeed on third attempt
                mock_run.side_effect = [
                    Exception("Build failed"),
                    Exception("Build failed again"),
                    "Successfully built abc123\nSuccessfully tagged test-pod-image:latest"
                ]
                
                image_name = await self.builder.build_image()
                
                # Verify 3 attempts were made
                self.assertEqual(mock_run.call_count, 3)
                self.assertEqual(image_name, "test-pod-image:latest")
        
        asyncio.run(run_test())
        print('Image build retry logic tested.')

    def test_tag_image(self) -> None:
        """
        Test image tagging.
        """
        print('Test: test_tag_image')
        
        async def run_test():
            with patch.object(self.builder, 'run_command', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = "tagged"
                
                await self.builder.tag_image("test-pod-image:latest")
                
                call_args = mock_run.call_args[0][0]
                self.assertIn('docker image tag', call_args)
                self.assertIn('test-pod-image:latest', call_args)
                self.assertIn(self.builder.repo_name, call_args)
        
        asyncio.run(run_test())
        print('Image tagging tested.')

    def test_docker_login_success(self) -> None:
        """
        Test successful docker login.
        """
        print('Test: test_docker_login_success')
        
        async def run_test():
            with patch.object(self.builder, 'run_command', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = "Login Succeeded"
                
                await self.builder.docker_login()
                
                call_args = mock_run.call_args[0][0]
                self.assertIn('docker login', call_args)
                self.assertIn(self.builder.repo_name, call_args)
        
        asyncio.run(run_test())
        print('Docker login tested.')

    def test_docker_push(self) -> None:
        """
        Test docker image push.
        """
        print('Test: test_docker_push')
        
        async def run_test():
            with patch.object(self.builder, 'run_command', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = "Pushed\ndigest: sha256:abc123"
                
                await self.builder.docker_push("test-pod-image:latest")
                
                call_args = mock_run.call_args[0][0]
                self.assertIn('docker image push', call_args)
                self.assertIn(self.builder.repo_name, call_args)
                self.assertIn('test-pod-image:latest', call_args)
        
        asyncio.run(run_test())
        print('Docker push tested.')

    def test_cleanup_images(self) -> None:
        """
        Test local image cleanup.
        """
        print('Test: test_cleanup_images')
        
        async def run_test():
            with patch.object(self.builder, 'run_command', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = "Deleted images"
                
                await self.builder.cleanup_images("test-pod-image:latest")
                
                call_args = mock_run.call_args[0][0]
                self.assertIn('docker rmi', call_args)
                self.assertIn('test-pod-image:latest', call_args)
        
        asyncio.run(run_test())
        print('Image cleanup tested.')


if __name__ == '__main__':
    import unittest
    unittest.main()
