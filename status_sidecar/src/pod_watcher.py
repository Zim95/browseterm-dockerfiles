# built-ins
import asyncio
import os
from typing import Callable

# third-party
from kubernetes_asyncio import client, config, watch

# module
from src.db_ops import UpdateContainerStatus
from src.config import CONTAINER_ID

# browseterm-db
from browseterm_db.operations import OperationResult


async def get_pod_info() -> tuple[str, str]:
    """Get the current pod's name and namespace."""
    # Get pod name from hostname (in K8s, hostname equals pod name)
    pod_name: str = os.getenv("POD_NAME") or os.getenv("HOSTNAME") or open("/etc/hostname").read().strip()

    # Get namespace from mounted service account secret
    namespace_file: str = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
    namespace: str = ""
    if os.path.exists(namespace_file):
        with open(namespace_file, "r") as f:
            namespace = f.read().strip()
    else:
        namespace = os.getenv("POD_NAMESPACE", "default")
    return pod_name, namespace


async def watch_pod_status(callback: Callable) -> None:
    """Watch the current pod and print status changes."""
    # Load in-cluster configuration
    try:
        config.load_incluster_config()
        print("Loaded in-cluster configuration")
    except Exception as e:
        print(f"Failed to load in-cluster config, trying kubeconfig: {e}")
        await config.load_kube_config()

    # Get current pod information
    pod_name, namespace = await get_pod_info()
    print(f"Watching pod: {pod_name} in namespace: {namespace}")

    # Create API client
    v1: client.CoreV1Api = client.CoreV1Api()

    # Keep watching indefinitely with retry logic
    retry_delay: int = 5
    while True:
        try:
            # Watch the specific pod
            w: watch.Watch = watch.Watch()
            print(f"Starting watch stream for pod {pod_name}...")
            async for event in w.stream(
                func=v1.list_namespaced_pod,
                namespace=namespace,
                field_selector=f"metadata.name={pod_name}",
                timeout_seconds=0
            ):
                pod: client.V1Pod = event['object']
                update_container_status: UpdateContainerStatus = UpdateContainerStatus(
                    container_id=CONTAINER_ID,
                    network=pod.metadata.namespace,
                    status=pod.status.phase
                )
                print(f"Updating container status: {update_container_status}")
                result: OperationResult = await callback(update_container_status)
                if not result.success:
                    print(f"Error updating container status: {result.error}")
                print(f"Container:  status updated")
        except asyncio.CancelledError:
            print("Watch task cancelled, shutting down...")
            break
        except Exception as e:
            print(f"Error watching pod: {e}")
            print(f"Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
            continue
    await v1.api_client.close()
