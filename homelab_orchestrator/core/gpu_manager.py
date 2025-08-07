"""GPU Resource Manager - Unified GPU resource discovery and management.

Handles local and remote GPU resource discovery, allocation, monitoring,
and integration with AI/ML workloads in the homelab environment.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from homelab_orchestrator.utils.command_utils import execute_command


if TYPE_CHECKING:
    from .config_manager import ConfigManager


@dataclass
class GPUResource:
    """GPU resource information."""

    gpu_id: str
    name: str
    memory_total: int  # MB
    memory_used: int  # MB
    utilization: float  # Percentage
    temperature: int | None = None  # Celsius
    location: str = "local"  # local, remote
    hostname: str | None = None
    driver_version: str | None = None
    cuda_version: str | None = None
    available: bool = True


@dataclass
class GPUAllocation:
    """GPU resource allocation."""

    allocation_id: str
    gpu_resource: GPUResource
    allocated_to: str  # Service/workload name
    allocation_time: datetime
    memory_allocated: int  # MB
    expected_duration: int | None = None  # minutes
    metadata: dict[str, Any] = field(default_factory=dict)


class GPUResourceManager:
    """Comprehensive GPU resource management system."""

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize GPU resource manager.

        Args:
            config_manager: Configuration manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager

        # GPU configuration
        self.gpu_config = config_manager.get_gpu_config()

        # Resource tracking
        self.discovered_gpus: dict[str, GPUResource] = {}
        self.allocations: dict[str, GPUAllocation] = {}

        # Monitoring state
        self.monitoring_active = False
        self.monitoring_task: asyncio.Task | None = None

        self.logger.info(
            f"GPU Manager initialized (enabled: {self.gpu_config.get('enabled', False)})",
        )

    async def start_monitoring(self) -> None:
        """Start GPU resource monitoring."""
        if not self.gpu_config.get("enabled", False):
            self.logger.info("GPU management disabled, skipping monitoring")
            return

        if self.monitoring_active:
            self.logger.warning("GPU monitoring already active")
            return

        self.logger.info("Starting GPU resource monitoring")
        self.monitoring_active = True

        # Initial discovery
        await self.discover_gpu_resources()

        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self) -> None:
        """Stop GPU resource monitoring."""
        if not self.monitoring_active:
            return

        self.logger.info("Stopping GPU resource monitoring")
        self.monitoring_active = False

        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.monitoring_task

    async def _monitoring_loop(self) -> None:
        """Main GPU monitoring loop."""
        while self.monitoring_active:
            try:
                # Update GPU resource information
                await self.discover_gpu_resources()

                # Check allocation health
                await self._check_allocation_health()

                # Sleep for monitoring interval (5 minutes)
                await asyncio.sleep(300)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"GPU monitoring loop error: {e}")
                await asyncio.sleep(60)  # Back off on errors

    async def discover_gpu_resources(self) -> dict[str, Any]:
        """Discover available GPU resources.

        Returns:
            Discovery results with found GPU resources
        """
        self.logger.info("Discovering GPU resources")

        discovery_config = self.gpu_config.get("discovery", {})
        discovered = {}

        try:
            # Discover local GPUs
            if discovery_config.get("local_gpus", True):
                local_gpus = await self._discover_local_gpus()
                discovered.update(local_gpus)

            # Discover remote GPUs
            if discovery_config.get("remote_gpus", False):
                remote_gpus = await self._discover_remote_gpus()
                discovered.update(remote_gpus)

            # Update discovered GPUs
            self.discovered_gpus = discovered

            self.logger.info(f"Discovered {len(discovered)} GPU resources")

            return {
                "success": True,
                "gpus_found": len(discovered),
                "gpus": {gpu_id: self._gpu_to_dict(gpu) for gpu_id, gpu in discovered.items()},
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.exception(f"GPU discovery failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "gpus_found": 0,
                "timestamp": datetime.now().isoformat(),
            }

    async def _discover_local_gpus(self) -> dict[str, GPUResource]:
        """Discover local GPU resources using nvidia-smi."""
        local_gpus = {}

        try:
            # Check if nvidia-smi is available
            returncode, _, _ = await execute_command(
                ["which", "nvidia-smi"],
                allowed_commands=["which"],
                check=False,
            )

            if returncode != 0:
                self.logger.debug("nvidia-smi not available, skipping local GPU discovery")
                return local_gpus

            # Query GPU information
            cmd = [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,memory.used,utilization.gpu,temperature.gpu,driver_version",
                "--format=csv,noheader,nounits",
            ]

            returncode, stdout, stderr = await execute_command(
                cmd,
                allowed_commands=["nvidia-smi"],
                check=False,
            )

            if returncode != 0:
                self.logger.warning(f"nvidia-smi query failed: {stderr.decode()}")
                return local_gpus

            # Parse nvidia-smi output
            for line in stdout.decode().strip().split("\n"):
                if not line.strip():
                    continue

                try:
                    parts = [part.strip() for part in line.split(",")]
                    if len(parts) >= 7:
                        gpu_id = f"local-gpu-{parts[0]}"
                        gpu = GPUResource(
                            gpu_id=gpu_id,
                            name=parts[1],
                            memory_total=int(parts[2]),
                            memory_used=int(parts[3]),
                            utilization=float(parts[4]),
                            temperature=int(parts[5]) if parts[5] != "[N/A]" else None,
                            location="local",
                            driver_version=parts[6],
                        )

                        # Get CUDA version
                        cuda_version = await self._get_cuda_version()
                        gpu.cuda_version = cuda_version

                        local_gpus[gpu_id] = gpu

                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Failed to parse nvidia-smi line '{line}': {e}")

            self.logger.debug(f"Discovered {len(local_gpus)} local GPUs")

        except Exception as e:
            self.logger.exception(f"Local GPU discovery failed: {e}")

        return local_gpus

    async def _discover_remote_gpus(self) -> dict[str, GPUResource]:
        """Discover remote GPU resources."""
        remote_gpus = {}

        # This would implement remote GPU discovery
        # Could use SSH to remote nodes, Kubernetes node labels, etc.
        self.logger.debug("Remote GPU discovery not yet implemented")

        return remote_gpus

    async def _get_cuda_version(self) -> str | None:
        """Get CUDA version if available."""
        try:
            returncode, stdout, _ = await execute_command(
                ["nvidia-smi", "--query-gpu=driver_version"],
                allowed_commands=["nvidia-smi"],
                check=False,
            )

            if returncode == 0:
                # Simple CUDA version detection
                returncode, stdout, _ = await execute_command(
                    ["nvcc", "--version"],
                    allowed_commands=["nvcc"],
                    check=False,
                )

                if process.returncode == 0:
                    output = stdout.decode()
                    for line in output.split("\n"):
                        if "release" in line.lower():
                            # Extract version from line like "Cuda compilation tools, release 11.8, V11.8.89"
                            import re

                            match = re.search(r"release (\d+\.\d+)", line)
                            if match:
                                return match.group(1)

        except Exception:
            pass  # CUDA version not critical

        return None

    async def allocate_gpu_resource(
        self,
        service_name: str,
        memory_requirement: int,
        duration_minutes: int | None = None,
        gpu_preference: str | None = None,
    ) -> dict[str, Any]:
        """Allocate GPU resource to a service.

        Args:
            service_name: Name of service requesting GPU
            memory_requirement: Required GPU memory in MB
            duration_minutes: Expected duration of allocation
            gpu_preference: Preferred GPU ID (optional)

        Returns:
            Allocation result
        """
        self.logger.info(f"Allocating GPU resource for {service_name}")

        try:
            # Find suitable GPU
            suitable_gpu = None
            gpu_id = None

            if gpu_preference and gpu_preference in self.discovered_gpus:
                gpu = self.discovered_gpus[gpu_preference]
                if self._is_gpu_suitable(gpu, memory_requirement):
                    suitable_gpu = gpu
                    gpu_id = gpu_preference

            if not suitable_gpu:
                # Find best available GPU
                for gid, gpu in self.discovered_gpus.items():
                    if self._is_gpu_suitable(gpu, memory_requirement):
                        if not suitable_gpu or gpu.memory_total > suitable_gpu.memory_total:
                            suitable_gpu = gpu
                            gpu_id = gid

            if not suitable_gpu:
                return {
                    "success": False,
                    "error": "No suitable GPU found",
                    "requirements": {
                        "memory_required": memory_requirement,
                        "gpus_available": len(self.discovered_gpus),
                    },
                    "recommendations": [
                        "Reduce memory requirements or wait for GPU availability",
                    ],
                }

            # Create allocation
            allocation_id = f"{service_name}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            allocation = GPUAllocation(
                allocation_id=allocation_id,
                gpu_resource=suitable_gpu,
                allocated_to=service_name,
                allocation_time=datetime.now(),
                memory_allocated=memory_requirement,
                expected_duration=duration_minutes,
            )

            # Mark GPU as allocated
            suitable_gpu.available = False
            self.allocations[allocation_id] = allocation

            self.logger.info(
                f"GPU {gpu_id} allocated to {service_name} (allocation: {allocation_id})",
            )

            return {
                "success": True,
                "allocation_id": allocation_id,
                "gpu_id": gpu_id,
                "gpu_name": suitable_gpu.name,
                "memory_allocated": memory_requirement,
                "memory_available": suitable_gpu.memory_total - suitable_gpu.memory_used,
                "timestamp": allocation.allocation_time.isoformat(),
            }

        except Exception as e:
            self.logger.exception(f"GPU allocation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "recommendations": ["Check GPU manager logs for details"],
            }

    def _is_gpu_suitable(self, gpu: GPUResource, memory_requirement: int) -> bool:
        """Check if GPU is suitable for allocation.

        Args:
            gpu: GPU resource to check
            memory_requirement: Required memory in MB

        Returns:
            True if GPU is suitable
        """
        if not gpu.available:
            return False

        available_memory = gpu.memory_total - gpu.memory_used
        if available_memory < memory_requirement:
            return False

        # Check utilization threshold
        if gpu.utilization > 80.0:  # Don't allocate heavily used GPUs
            return False

        return True

    async def release_gpu_resource(self, allocation_id: str) -> dict[str, Any]:
        """Release allocated GPU resource.

        Args:
            allocation_id: Allocation ID to release

        Returns:
            Release result
        """
        self.logger.info(f"Releasing GPU allocation: {allocation_id}")

        try:
            if allocation_id not in self.allocations:
                return {
                    "success": False,
                    "error": f"Allocation {allocation_id} not found",
                }

            allocation = self.allocations[allocation_id]

            # Mark GPU as available
            gpu_resource = allocation.gpu_resource
            gpu_resource.available = True

            # Remove allocation
            del self.allocations[allocation_id]

            # Calculate usage duration
            duration = (datetime.now() - allocation.allocation_time).total_seconds() / 60

            self.logger.info(
                f"GPU {gpu_resource.gpu_id} released from {allocation.allocated_to} "
                f"(duration: {duration:.1f} minutes)",
            )

            return {
                "success": True,
                "gpu_id": gpu_resource.gpu_id,
                "service": allocation.allocated_to,
                "duration_minutes": duration,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.exception(f"GPU release failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def get_resource_status(self) -> dict[str, Any]:
        """Get current GPU resource status.

        Returns:
            Resource status information
        """
        try:
            # Update resource information
            await self.discover_gpu_resources()

            total_gpus = len(self.discovered_gpus)
            available_gpus = sum(1 for gpu in self.discovered_gpus.values() if gpu.available)
            active_allocations = len(self.allocations)

            return {
                "status": "healthy" if total_gpus > 0 else "no_gpus",
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_gpus": total_gpus,
                    "available_gpus": available_gpus,
                    "allocated_gpus": total_gpus - available_gpus,
                    "active_allocations": active_allocations,
                },
                "gpus": {
                    gpu_id: self._gpu_to_dict(gpu) for gpu_id, gpu in self.discovered_gpus.items()
                },
                "allocations": {
                    alloc_id: self._allocation_to_dict(alloc)
                    for alloc_id, alloc in self.allocations.items()
                },
            }

        except Exception as e:
            self.logger.exception(f"Failed to get GPU resource status: {e}")
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "summary": {"total_gpus": 0, "available_gpus": 0, "allocated_gpus": 0},
            }

    async def setup_gpu_resources(self) -> dict[str, Any]:
        """Setup GPU resources for the homelab environment.

        Returns:
            Setup result
        """
        if not self.gpu_config.get("enabled", False):
            return {
                "success": True,
                "message": "GPU resources disabled in configuration",
                "gpus_configured": 0,
            }

        self.logger.info("Setting up GPU resources")

        try:
            # Discover available GPUs
            discovery_result = await self.discover_gpu_resources()

            if not discovery_result["success"]:
                return {
                    "success": False,
                    "error": "GPU discovery failed",
                    "details": discovery_result,
                }

            gpus_found = discovery_result["gpus_found"]

            # Setup GPU device plugin for Kubernetes (if needed)
            setup_results = []
            if gpus_found > 0:
                device_plugin_result = await self._setup_nvidia_device_plugin()
                setup_results.append(device_plugin_result)

            return {
                "success": True,
                "message": f"GPU resources setup completed ({gpus_found} GPUs)",
                "gpus_configured": gpus_found,
                "setup_results": setup_results,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.exception(f"GPU resource setup failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "gpus_configured": 0,
            }

    async def _setup_nvidia_device_plugin(self) -> dict[str, Any]:
        """Setup NVIDIA device plugin for Kubernetes."""
        try:
            # Check if device plugin is already deployed
            cmd = [
                "kubectl",
                "get",
                "daemonset",
                "nvidia-device-plugin-daemonset",
                "-n",
                "kube-system",
            ]

            returncode, _, _ = await execute_command(
                cmd,
                allowed_commands=["kubectl"],
                check=False,
            )

            if returncode == 0:
                return {
                    "success": True,
                    "message": "NVIDIA device plugin already deployed",
                    "action": "skipped",
                }

            # Deploy NVIDIA device plugin
            cmd = [
                "kubectl",
                "apply",
                "-f",
                "https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.1/nvidia-device-plugin.yml",
            ]

            returncode, stdout, stderr = await execute_command(
                cmd,
                allowed_commands=["kubectl"],
                check=False,
            )

            if returncode == 0:
                return {
                    "success": True,
                    "message": "NVIDIA device plugin deployed successfully",
                    "action": "deployed",
                }
            return {
                "success": False,
                "message": f"NVIDIA device plugin deployment failed: {stderr.decode()}",
                "action": "failed",
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Device plugin setup failed: {e}",
                "action": "error",
            }

    async def check_gpu_health(self) -> dict[str, Any]:
        """Check GPU health status.

        Returns:
            GPU health check results
        """
        try:
            await self.discover_gpu_resources()

            issues = []
            warnings = []

            for gpu_id, gpu in self.discovered_gpus.items():
                # Check temperature
                if gpu.temperature and gpu.temperature > 85:
                    warnings.append(f"GPU {gpu_id} temperature high: {gpu.temperature}°C")

                # Check utilization
                if gpu.utilization > 95:
                    warnings.append(f"GPU {gpu_id} utilization high: {gpu.utilization}%")

                # Check memory usage
                memory_percent = (gpu.memory_used / gpu.memory_total) * 100
                if memory_percent > 90:
                    warnings.append(f"GPU {gpu_id} memory usage high: {memory_percent:.1f}%")

            status = "healthy"
            if issues:
                status = "unhealthy"
            elif warnings:
                status = "warning"

            return {
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "gpus_checked": len(self.discovered_gpus),
                "issues": issues,
                "warnings": warnings,
                "recommendations": warnings + issues if warnings or issues else [],
            }

        except Exception as e:
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "gpus_checked": 0,
            }

    async def _check_allocation_health(self) -> None:
        """Check health of current GPU allocations."""
        current_time = datetime.now()

        for allocation_id, allocation in list(self.allocations.items()):
            # Check for stale allocations (over expected duration)
            if allocation.expected_duration:
                elapsed_minutes = (current_time - allocation.allocation_time).total_seconds() / 60

                if elapsed_minutes > allocation.expected_duration * 1.5:  # 50% buffer
                    self.logger.warning(
                        f"GPU allocation {allocation_id} exceeded expected duration "
                        f"({elapsed_minutes:.1f}m vs {allocation.expected_duration}m)",
                    )

    def _gpu_to_dict(self, gpu: GPUResource) -> dict[str, Any]:
        """Convert GPU resource to dictionary."""
        return {
            "gpu_id": gpu.gpu_id,
            "name": gpu.name,
            "memory_total": gpu.memory_total,
            "memory_used": gpu.memory_used,
            "memory_available": gpu.memory_total - gpu.memory_used,
            "utilization": gpu.utilization,
            "temperature": gpu.temperature,
            "location": gpu.location,
            "hostname": gpu.hostname,
            "driver_version": gpu.driver_version,
            "cuda_version": gpu.cuda_version,
            "available": gpu.available,
        }

    def _allocation_to_dict(self, allocation: GPUAllocation) -> dict[str, Any]:
        """Convert GPU allocation to dictionary."""
        return {
            "allocation_id": allocation.allocation_id,
            "gpu_id": allocation.gpu_resource.gpu_id,
            "allocated_to": allocation.allocated_to,
            "allocation_time": allocation.allocation_time.isoformat(),
            "memory_allocated": allocation.memory_allocated,
            "expected_duration": allocation.expected_duration,
            "metadata": allocation.metadata,
        }
