"""Remote Cluster Manager - Unified remote server and cluster integration.

Handles remote Kubernetes clusters, SSH connections to remote servers,
and hybrid local/remote deployments for distributed homelab environments.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import paramiko
import yaml


if TYPE_CHECKING:
    from homelab_orchestrator.core.config_manager import ConfigManager


@dataclass
class RemoteServer:
    """Remote server configuration."""

    hostname: str
    ip_address: str
    username: str
    ssh_key_path: str | None = None
    ssh_password: str | None = None
    port: int = 22
    description: str = ""
    tags: list[str] = field(default_factory=list)
    gpu_enabled: bool = False
    last_contact: datetime | None = None
    status: str = "unknown"  # unknown, online, offline, error


@dataclass
class RemoteCluster:
    """Remote Kubernetes cluster configuration."""

    name: str
    kubeconfig_path: str
    context_name: str | None = None
    server_endpoint: str = ""
    description: str = ""
    gpu_nodes: list[str] = field(default_factory=list)
    last_health_check: datetime | None = None
    status: str = "unknown"  # unknown, healthy, degraded, unreachable


class ClusterManager:
    """Comprehensive remote server and cluster management."""

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize cluster manager.

        Args:
            config_manager: Configuration manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager

        # Remote resources
        self.remote_servers: dict[str, RemoteServer] = {}
        self.remote_clusters: dict[str, RemoteCluster] = {}

        # SSH connections pool
        self.ssh_connections: dict[str, paramiko.SSHClient] = {}

        # Load remote configuration
        self._load_remote_configuration()

    def _load_remote_configuration(self) -> None:
        """Load remote server and cluster configuration."""
        # This would load from configuration files or environment
        # For now, we'll set up defaults based on cluster type

        cluster_type = self.config_manager.context.cluster_type

        if cluster_type in ["remote", "hybrid"]:
            # Example remote server configuration
            # In production, this would come from secure configuration
            self.add_remote_server(
                RemoteServer(
                    hostname="gpu-server-1",
                    ip_address="192.168.1.100",
                    username="homelab",
                    ssh_key_path="~/.ssh/homelab_rsa",
                    description="Primary GPU server",
                    tags=["gpu", "ai-ml"],
                    gpu_enabled=True,
                ),
            )

            # Example remote cluster configuration
            self.add_remote_cluster(
                RemoteCluster(
                    name="remote-k3s",
                    kubeconfig_path="~/.kube/remote-config",
                    context_name="remote-k3s",
                    description="Remote K3s cluster",
                    gpu_nodes=["gpu-node-1", "gpu-node-2"],
                ),
            )

        self.logger.info(
            f"Loaded {len(self.remote_servers)} servers, {len(self.remote_clusters)} clusters",
        )

    def add_remote_server(self, server: RemoteServer) -> None:
        """Add remote server to management.

        Args:
            server: Remote server configuration
        """
        self.remote_servers[server.hostname] = server
        self.logger.debug(f"Added remote server: {server.hostname}")

    def add_remote_cluster(self, cluster: RemoteCluster) -> None:
        """Add remote cluster to management.

        Args:
            cluster: Remote cluster configuration
        """
        self.remote_clusters[cluster.name] = cluster
        self.logger.debug(f"Added remote cluster: {cluster.name}")

    async def check_cluster_health(self) -> dict[str, Any]:
        """Check health of all managed clusters.

        Returns:
            Cluster health status
        """
        self.logger.info("Checking cluster health")

        health_results = {
            "overall_status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "clusters": {},
            "servers": {},
            "issues": [],
            "recommendations": [],
        }

        try:
            # Check remote clusters
            cluster_tasks = [
                self._check_remote_cluster_health(cluster)
                for cluster in self.remote_clusters.values()
            ]

            if cluster_tasks:
                cluster_results = await asyncio.gather(*cluster_tasks, return_exceptions=True)

                for i, result in enumerate(cluster_results):
                    cluster_name = list(self.remote_clusters.keys())[i]

                    if isinstance(result, Exception):
                        health_results["clusters"][cluster_name] = {
                            "status": "error",
                            "error": str(result),
                        }
                        health_results["issues"].append(
                            f"Cluster {cluster_name} health check failed: {result}",
                        )
                    else:
                        health_results["clusters"][cluster_name] = result
                        if result.get("status") != "healthy":
                            health_results["issues"].append(
                                f"Cluster {cluster_name} is {result.get('status')}",
                            )

            # Check remote servers
            server_tasks = [
                self._check_remote_server_health(server) for server in self.remote_servers.values()
            ]

            if server_tasks:
                server_results = await asyncio.gather(*server_tasks, return_exceptions=True)

                for i, result in enumerate(server_results):
                    server_hostname = list(self.remote_servers.keys())[i]

                    if isinstance(result, Exception):
                        health_results["servers"][server_hostname] = {
                            "status": "error",
                            "error": str(result),
                        }
                        health_results["issues"].append(
                            f"Server {server_hostname} health check failed: {result}",
                        )
                    else:
                        health_results["servers"][server_hostname] = result
                        if result.get("status") != "online":
                            health_results["issues"].append(
                                f"Server {server_hostname} is {result.get('status')}",
                            )

            # Determine overall status
            if health_results["issues"]:
                if any("error" in issue.lower() for issue in health_results["issues"]):
                    health_results["overall_status"] = "critical"
                else:
                    health_results["overall_status"] = "degraded"

            # Generate recommendations
            if health_results["issues"]:
                health_results["recommendations"] = [
                    "Review cluster and server connectivity",
                    "Check network configuration and firewall rules",
                    "Verify SSH keys and authentication",
                ]

            return health_results

        except Exception as e:
            self.logger.exception(f"Cluster health check failed: {e}")
            return {
                "overall_status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "clusters": {},
                "servers": {},
                "issues": [f"Health check failed: {e}"],
                "recommendations": ["Check cluster manager logs"],
            }

    async def _check_remote_cluster_health(self, cluster: RemoteCluster) -> dict[str, Any]:
        """Check health of a specific remote cluster.

        Args:
            cluster: Remote cluster to check

        Returns:
            Cluster health status
        """
        try:
            # Check if kubeconfig exists
            kubeconfig_path = Path(cluster.kubeconfig_path).expanduser()
            if not kubeconfig_path.exists():
                return {
                    "status": "error",
                    "message": f"Kubeconfig not found: {kubeconfig_path}",
                    "last_checked": datetime.now().isoformat(),
                }

            # Test cluster connectivity
            cmd = ["kubectl", "--kubeconfig", str(kubeconfig_path), "cluster-info"]

            if cluster.context_name:
                cmd.extend(["--context", cluster.context_name])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)

            if process.returncode == 0:
                # Get node information
                node_cmd = ["kubectl", "--kubeconfig", str(kubeconfig_path), "get", "nodes"]
                if cluster.context_name:
                    node_cmd.extend(["--context", cluster.context_name])

                node_process = await asyncio.create_subprocess_exec(
                    *node_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                node_stdout, _ = await node_process.communicate()
                node_count = len(node_stdout.decode().strip().split("\n")) - 1  # Exclude header

                # Update cluster status
                cluster.status = "healthy"
                cluster.last_health_check = datetime.now()

                return {
                    "status": "healthy",
                    "message": "Cluster accessible",
                    "node_count": node_count,
                    "server_endpoint": cluster.server_endpoint,
                    "last_checked": cluster.last_health_check.isoformat(),
                }
            cluster.status = "unreachable"
            return {
                "status": "unreachable",
                "message": f"Cluster unreachable: {stderr.decode()}",
                "last_checked": datetime.now().isoformat(),
            }

        except asyncio.TimeoutError:
            cluster.status = "timeout"
            return {
                "status": "timeout",
                "message": "Cluster health check timed out",
                "last_checked": datetime.now().isoformat(),
            }
        except Exception as e:
            cluster.status = "error"
            return {
                "status": "error",
                "message": f"Health check failed: {e}",
                "last_checked": datetime.now().isoformat(),
            }

    async def _check_remote_server_health(self, server: RemoteServer) -> dict[str, Any]:
        """Check health of a specific remote server.

        Args:
            server: Remote server to check

        Returns:
            Server health status
        """
        try:
            # Test SSH connectivity
            ssh_client = await self._get_ssh_connection(server)

            if ssh_client and ssh_client.get_transport() and ssh_client.get_transport().is_active():
                # Execute basic health command
                stdin, stdout, stderr = ssh_client.exec_command("uptime")
                uptime_output = stdout.read().decode().strip()

                # Get system information
                stdin, stdout, stderr = ssh_client.exec_command("uname -a")
                system_info = stdout.read().decode().strip()

                server.status = "online"
                server.last_contact = datetime.now()

                return {
                    "status": "online",
                    "message": "Server accessible via SSH",
                    "uptime": uptime_output,
                    "system_info": system_info,
                    "gpu_enabled": server.gpu_enabled,
                    "last_contact": server.last_contact.isoformat(),
                }
            server.status = "offline"
            return {
                "status": "offline",
                "message": "SSH connection failed",
                "last_checked": datetime.now().isoformat(),
            }

        except Exception as e:
            server.status = "error"
            return {
                "status": "error",
                "message": f"Server check failed: {e}",
                "last_checked": datetime.now().isoformat(),
            }

    async def _get_ssh_connection(self, server: RemoteServer) -> paramiko.SSHClient | None:
        """Get SSH connection to remote server.

        Args:
            server: Remote server configuration

        Returns:
            SSH client connection or None
        """
        try:
            # Check if we have an existing connection
            if server.hostname in self.ssh_connections:
                ssh_client = self.ssh_connections[server.hostname]
                if ssh_client.get_transport() and ssh_client.get_transport().is_active():
                    return ssh_client
                # Remove stale connection
                del self.ssh_connections[server.hostname]

            # Create new SSH connection
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Prepare connection parameters
            connect_kwargs = {
                "hostname": server.ip_address,
                "port": server.port,
                "username": server.username,
                "timeout": 10,
            }

            # Use SSH key if specified
            if server.ssh_key_path:
                key_path = Path(server.ssh_key_path).expanduser()
                if key_path.exists():
                    connect_kwargs["key_filename"] = str(key_path)
                else:
                    self.logger.warning(f"SSH key not found: {key_path}")

            # Use password if specified and no key
            if server.ssh_password and not server.ssh_key_path:
                connect_kwargs["password"] = server.ssh_password

            # Connect
            ssh_client.connect(**connect_kwargs)

            # Store connection
            self.ssh_connections[server.hostname] = ssh_client

            return ssh_client

        except Exception as e:
            self.logger.exception(f"SSH connection to {server.hostname} failed: {e}")
            return None

    async def execute_remote_command(
        self,
        server_hostname: str,
        command: str,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Execute command on remote server.

        Args:
            server_hostname: Hostname of remote server
            command: Command to execute
            timeout: Command timeout in seconds

        Returns:
            Command execution result
        """
        if server_hostname not in self.remote_servers:
            return {
                "success": False,
                "error": f"Unknown server: {server_hostname}",
            }

        server = self.remote_servers[server_hostname]

        try:
            ssh_client = await self._get_ssh_connection(server)
            if not ssh_client:
                return {
                    "success": False,
                    "error": "SSH connection failed",
                }

            # Execute command
            stdin, stdout, stderr = ssh_client.exec_command(command)

            # Wait for command completion with timeout
            channel = stdout.channel
            channel.settimeout(timeout)

            stdout_data = stdout.read().decode()
            stderr_data = stderr.read().decode()
            return_code = channel.recv_exit_status()

            return {
                "success": return_code == 0,
                "return_code": return_code,
                "stdout": stdout_data,
                "stderr": stderr_data,
                "command": command,
                "server": server_hostname,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command,
                "server": server_hostname,
            }

    async def deploy_to_remote_cluster(
        self,
        cluster_name: str,
        manifests: list[dict[str, Any]],
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Deploy resources to remote cluster.

        Args:
            cluster_name: Name of remote cluster
            manifests: Kubernetes manifests to deploy
            namespace: Target namespace

        Returns:
            Deployment result
        """
        if cluster_name not in self.remote_clusters:
            return {
                "success": False,
                "error": f"Unknown cluster: {cluster_name}",
            }

        cluster = self.remote_clusters[cluster_name]

        try:
            # Create temporary manifest file
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                for manifest in manifests:
                    yaml.dump(manifest, f)
                    f.write("---\n")
                temp_file = f.name

            # Apply manifests to remote cluster
            cmd = ["kubectl", "--kubeconfig", cluster.kubeconfig_path, "apply", "-f", temp_file]

            if cluster.context_name:
                cmd.extend(["--context", cluster.context_name])

            if namespace:
                cmd.extend(["-n", namespace])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            # Clean up temp file
            Path(temp_file).unlink(missing_ok=True)

            if process.returncode == 0:
                return {
                    "success": True,
                    "message": "Deployment successful",
                    "cluster": cluster_name,
                    "manifests_applied": len(manifests),
                    "output": stdout.decode(),
                }
            return {
                "success": False,
                "error": f"Deployment failed: {stderr.decode()}",
                "cluster": cluster_name,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "cluster": cluster_name,
            }

    async def discover_remote_gpu_resources(self) -> dict[str, Any]:
        """Discover GPU resources on remote servers.

        Returns:
            GPU discovery results
        """
        gpu_resources = {}

        # Check each GPU-enabled server
        for hostname, server in self.remote_servers.items():
            if not server.gpu_enabled:
                continue

            try:
                # Execute nvidia-smi on remote server
                result = await self.execute_remote_command(
                    hostname,
                    "nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu --format=csv,noheader,nounits",
                    timeout=15,
                )

                if result["success"] and result["stdout"]:
                    gpu_data = []
                    for line in result["stdout"].strip().split("\n"):
                        if line.strip():
                            parts = [part.strip() for part in line.split(",")]
                            if len(parts) >= 5:
                                gpu_data.append(
                                    {
                                        "gpu_id": f"{hostname}-gpu-{parts[0]}",
                                        "name": parts[1],
                                        "memory_total": int(parts[2]),
                                        "memory_used": int(parts[3]),
                                        "utilization": float(parts[4]),
                                        "location": "remote",
                                        "hostname": hostname,
                                    },
                                )

                    gpu_resources[hostname] = {
                        "gpus": gpu_data,
                        "gpu_count": len(gpu_data),
                        "status": "accessible",
                    }
                else:
                    gpu_resources[hostname] = {
                        "gpus": [],
                        "gpu_count": 0,
                        "status": "no_gpus_or_error",
                        "error": result.get("error", "No GPU data returned"),
                    }

            except Exception as e:
                gpu_resources[hostname] = {
                    "gpus": [],
                    "gpu_count": 0,
                    "status": "error",
                    "error": str(e),
                }

        total_gpus = sum(data.get("gpu_count", 0) for data in gpu_resources.values())

        return {
            "success": True,
            "servers_checked": len([s for s in self.remote_servers.values() if s.gpu_enabled]),
            "total_gpus_found": total_gpus,
            "servers": gpu_resources,
            "timestamp": datetime.now().isoformat(),
        }

    def get_cluster_status(self) -> dict[str, Any]:
        """Get current status of all managed clusters and servers.

        Returns:
            Cluster management status
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "cluster_type": self.config_manager.context.cluster_type,
            "remote_servers": {
                hostname: {
                    "hostname": server.hostname,
                    "ip_address": server.ip_address,
                    "status": server.status,
                    "gpu_enabled": server.gpu_enabled,
                    "tags": server.tags,
                    "last_contact": server.last_contact.isoformat()
                    if server.last_contact
                    else None,
                }
                for hostname, server in self.remote_servers.items()
            },
            "remote_clusters": {
                name: {
                    "name": cluster.name,
                    "status": cluster.status,
                    "server_endpoint": cluster.server_endpoint,
                    "gpu_nodes": cluster.gpu_nodes,
                    "last_health_check": (
                        cluster.last_health_check.isoformat() if cluster.last_health_check else None
                    ),
                }
                for name, cluster in self.remote_clusters.items()
            },
            "active_ssh_connections": len(self.ssh_connections),
        }

    async def cleanup(self) -> None:
        """Clean up resources and connections."""
        # Close SSH connections
        for hostname, ssh_client in self.ssh_connections.items():
            try:
                ssh_client.close()
                self.logger.debug(f"Closed SSH connection to {hostname}")
            except Exception as e:
                self.logger.warning(f"Error closing SSH connection to {hostname}: {e}")

        self.ssh_connections.clear()
        self.logger.info("Cluster manager cleanup completed")
