"""Snapshot builder - handles Docker image building and pushing."""
import asyncio
import os
import time
from typing import Optional


class SnapshotBuilder:
    """
    Builds and pushes Docker images from filesystem snapshots.
    
    Runs inside the snapshot Job: unpacks the filesystem snapshot, builds a Docker
    image from it, and pushes it to the registry.
    """
    
    def __init__(
        self,
        snapshot_path: str,
        container_id: str,
        repo_name: str,
        repo_password: str,
        namespace_name: str,
        pod_name: str,
        snapshot_dir: str
    ):
        """
        Initialize the snapshot builder.
        
        :param snapshot_path: Full path to the snapshot tar file
        :param container_id: Database ID of the container
        :param repo_name: Docker registry repository name
        :param repo_password: Docker registry password
        :param namespace_name: Kubernetes namespace name
        :param pod_name: Kubernetes pod name
        :param snapshot_dir: Base snapshot directory
        """
        self.snapshot_path = snapshot_path
        self.snapshot_base_dir = snapshot_dir
        self.snapshot_file_name = os.path.basename(snapshot_path)
        self.container_id = container_id
        self.namespace_name = namespace_name
        self.pod_name = pod_name
        self.repo_name = repo_name
        self.repo_password = repo_password
        
        # Build directory for this container
        self.build_dir = os.path.join(self.snapshot_base_dir, namespace_name, pod_name, "build")
        
        # Retry configuration
        self.docker_login_max_retries = 3
        self.docker_login_retry_delay = 2.0
        self.docker_build_max_retries = 3
        self.docker_build_retry_delay = 5.0
    
    async def run_command(self, command: str, timeout: Optional[int] = None) -> str:
        """
        Run a shell command asynchronously.
        
        :param command: Command to execute
        :param timeout: Optional timeout in seconds
        :return: Command output
        """
        print(f"Running command: {command}")
        
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            output = stdout.decode() if stdout else ""
            
            if process.returncode != 0:
                raise Exception(f"Command failed with return code {process.returncode}: {output}")
            
            return output
            
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"Command timed out after {timeout} seconds")
    
    async def unpack_tar(self) -> None:
        """
        Unpack the tar file into the rootfs directory.
        """
        try:
            untar_cmd = (
                f"mkdir -p {self.build_dir}/rootfs && "
                f"tar -xzf {self.snapshot_path} "
                f"-C {self.build_dir}/rootfs"
            )
            await self.run_command(untar_cmd)
            print("✓ Filesystem snapshot unpacked")
        except Exception as e:
            raise Exception(f"Failed to unpack tar file: {e}")
    
    async def create_dockerfile(self) -> None:
        """
        Create a Dockerfile in the rootfs directory.
        """
        try:
            dockerfile_content = (
                "FROM scratch\n"
                "COPY . /\n"
                'ENTRYPOINT ["/entrypoint.sh"]\n'
            )
            
            dockerfile_path = f"{self.build_dir}/rootfs/Dockerfile"
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content)
            
            print("✓ Dockerfile created")
        except Exception as e:
            raise Exception(f"Failed to create Dockerfile: {e}")
    
    async def build_image(self) -> str:
        """
        Build a Docker image from the rootfs directory.
        
        :return: Image name (e.g., "mycontainer-pod-image:latest")
        """
        # Generate image name from pod name
        image_name = f"{self.pod_name}-image:latest"
        
        build_cmd = (
            f"docker image build -t {image_name} "
            f"-f {self.build_dir}/rootfs/Dockerfile "
            f"{self.build_dir}/rootfs"
        )
        
        # Retry logic for builds
        last_error = None
        last_output = None
        for attempt in range(1, self.docker_build_max_retries + 1):
            try:
                print(f"Building image (attempt {attempt}/{self.docker_build_max_retries})...")
                output = await self.run_command(build_cmd, timeout=1500)  # 25 minutes
                last_output = output
                
                # Check for success indicators - support both old and new Docker BuildKit format
                # Old format: "Successfully built <hash>" or "Successfully tagged <image>"
                # New BuildKit format: "writing image sha256:..." and "naming to docker.io/..." with "done"
                old_format_success = "Successfully built" in output or "Successfully tagged" in output
                buildkit_success = (
                    "writing image sha256:" in output and 
                    "naming to docker.io" in output and
                    "done" in output
                )
                
                if old_format_success or buildkit_success:
                    print(f"✓ Image built successfully: {image_name}")
                    return image_name
                else:
                    # Build command ran but didn't produce success indicators
                    last_error = f"Build completed but no success indicators found. Output:\n{output[-500:]}"
                    if attempt < self.docker_build_max_retries:
                        delay = self.docker_build_retry_delay * (2 ** (attempt - 1))
                        print(f"Build unclear (attempt {attempt}), retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        continue
                
            except Exception as e:
                last_error = str(e)
                print(f"Build error (attempt {attempt}): {str(e)[:200]}")
                if attempt < self.docker_build_max_retries:
                    delay = self.docker_build_retry_delay * (2 ** (attempt - 1))
                    print(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
        
        raise Exception(f"Failed to build image after {self.docker_build_max_retries} attempts. Last error: {last_error}")
    
    async def tag_image(self, image_name: str) -> None:
        """
        Tag the image for the registry.
        
        :param image_name: Local image name
        """
        try:
            tag_cmd = f"docker image tag {image_name} {self.repo_name}/{image_name}"
            await self.run_command(tag_cmd)
            print(f"✓ Image tagged: {self.repo_name}/{image_name}")
        except Exception as e:
            raise Exception(f"Failed to tag image: {e}")
    
    async def docker_login(self) -> None:
        """
        Login to the Docker registry with retry logic.
        """
        login_cmd = f"docker login -u {self.repo_name} -p {self.repo_password}"
        
        for attempt in range(1, self.docker_login_max_retries + 1):
            try:
                print(f"Logging into Docker registry (attempt {attempt}/{self.docker_login_max_retries})...")
                output = await self.run_command(login_cmd, timeout=30)
                
                if "Login Succeeded" in output:
                    print("✓ Docker registry login successful")
                    return
                
                # Check for retryable errors
                if attempt < self.docker_login_max_retries:
                    delay = self.docker_login_retry_delay * (2 ** (attempt - 1))
                    print(f"Login failed, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                
            except Exception as e:
                if attempt < self.docker_login_max_retries:
                    delay = self.docker_login_retry_delay * (2 ** (attempt - 1))
                    print(f"Login error: {e}, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                raise
        
        raise Exception(f"Failed to login after {self.docker_login_max_retries} attempts")
    
    async def docker_push(self, image_name: str) -> None:
        """
        Push the image to the Docker registry.
        
        :param image_name: Image name to push
        """
        try:
            push_cmd = f"docker image push {self.repo_name}/{image_name}"
            print(f"Pushing image to registry...")
            output = await self.run_command(push_cmd, timeout=1500)  # 25 minutes
            
            if "Pushed" in output or "digest:" in output:
                print(f"✓ Image pushed successfully: {self.repo_name}/{image_name}")
            else:
                raise Exception(f"Push may have failed: {output[-200:]}")
                
        except Exception as e:
            raise Exception(f"Failed to push image: {e}")
    
    async def cleanup_images(self, image_name: str) -> None:
        """
        Delete local Docker images to free up space.
        
        :param image_name: Local image name
        """
        try:
            local_image = image_name
            tagged_image = f"{self.repo_name}/{image_name}"
            
            delete_cmd = f"docker rmi {local_image} {tagged_image}"
            await self.run_command(delete_cmd)
            
            print(f"✓ Local images deleted: {local_image}, {tagged_image}")
        except Exception as e:
            # Don't fail the job if cleanup fails
            print(f"Warning: Failed to cleanup images: {e}")
