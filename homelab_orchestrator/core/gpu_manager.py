"""GPU resource discovery and management."""

import logging
from dataclasses import dataclass
from typing import List, Optional

from ..utils.async_command import execute_command_async

logger = logging.getLogger(__name__)

@dataclass
class GpuInfo:
    """Information about a GPU device."""
    index: int
    name: str
    memory_total: int  # MB
    memory_used: int   # MB
    driver_version: str = ""
    cuda_version: str = ""

class GpuManager:
    """Manages GPU resource discovery and monitoring."""

    def __init__(self) -> None:
        """Initialize GPU manager."""
        self.logger = logging.getLogger(__name__)

    async def is_nvidia_available(self) -> bool:
        """Check if NVIDIA tools are available."""
        try:
            returncode, _, _ = await execute_command_async(
                ["which", "nvidia-smi"],
                allowed_commands=["which"],
                check=False,
            )
            return returncode == 0
        except Exception as e:
            self.logger.debug(f"Error checking nvidia-smi: {e}")
            return False

    async def get_local_gpus(self) -> List[GpuInfo]:
        """Discover local NVIDIA GPUs."""
        local_gpus = []

        if not await self.is_nvidia_available():
            self.logger.debug("nvidia-smi not available, skipping local GPU discovery")
            return local_gpus

        try:
            # Get GPU list with nvidia-smi
            cmd = [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,memory.used",
                "--format=csv,noheader,nounits"
            ]
            returncode, stdout, stderr = await execute_command_async(
                cmd,
                allowed_commands=["nvidia-smi"],
                check=False,
            )

            if returncode != 0:
                self.logger.warning(f"nvidia-smi query failed: {stderr}")
                return local_gpus

            # Parse GPU info
            for line in stdout.splitlines():
                try:
                    index, name, total, used = line.split(",")
                    gpu = GpuInfo(
                        index=int(index),
                        name=name.strip(),
                        memory_total=int(float(total)),
                        memory_used=int(float(used))
                    )
                    local_gpus.append(gpu)
                except ValueError as e:
                    self.logger.warning(f"Failed to parse GPU info line '{line}': {e}")
                    continue

            # Get driver/CUDA versions if available
            versions = await self._get_versions()
            if versions:
                driver_ver, cuda_ver = versions
                for gpu in local_gpus:
                    gpu.driver_version = driver_ver
                    gpu.cuda_version = cuda_ver

        except Exception as e:
            self.logger.exception("Error discovering local GPUs")
            return []

        return local_gpus

    async def _get_versions(self) -> Optional[tuple[str, str]]:
        """Get NVIDIA driver and CUDA versions."""
        try:
            # Get driver version
            returncode, stdout, _ = await execute_command_async(
                ["nvidia-smi", "--query-gpu=driver_version"],
                allowed_commands=["nvidia-smi"],
                check=False,
            )

            if returncode == 0:
                driver_version = stdout.splitlines()[0].strip()

                # Get CUDA version
                returncode, stdout, _ = await execute_command_async(
                    ["nvidia-smi", "--query-gpu=cuda_version"],
                    allowed_commands=["nvidia-smi"],
                    check=False,
                )

                if returncode == 0:
                    cuda_version = stdout.splitlines()[0].strip()
                    return driver_version, cuda_version

        except Exception as e:
            self.logger.debug(f"Failed to get GPU versions: {e}")

        return None
