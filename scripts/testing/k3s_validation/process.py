#!/usr/bin/env python3
"""
K3s Process Executor for handling subprocess operations.

Copyright (c) 2025 Tyler Zervas
Licensed under the MIT License.
"""

import concurrent.futures
import logging
import subprocess
from pathlib import Path


class K3sProcessExecutor:
    """Handles subprocess execution and cleanup for K3s validation tests."""

    def __init__(self, timeout_config=None):
        """Initialize the process executor.

        Args:
            timeout_config: Optional configuration for operation timeouts.
                          Should have k3s_validation and cleanup_grace attributes.
        """
        self.logger = logging.getLogger(__name__)
        self.timeout_config = timeout_config

    def cleanup_on_timeout(self, proc: subprocess.Popen) -> None:
        """Gracefully terminate process tree on timeout.

        Args:
            proc: The subprocess.Popen object to clean up.
        """
        try:
            proc.terminate()
            try:
                proc.wait(timeout=self.timeout_config.cleanup_grace if self.timeout_config else 30)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")

    def execute_k3s_validation(self, cmd: list[str], workdir: Path) -> subprocess.CompletedProcess:
        """Execute K3s validation command with timeout handling.

        Args:
            cmd: Command to execute as a list of strings.
            workdir: Working directory for command execution.

        Returns:
            CompletedProcess instance with command results.

        Raises:
            subprocess.TimeoutExpired: If command execution times out.
            Exception: For other execution failures.
        """
        self.logger.debug(f"Executing command: {' '.join(cmd)}")
        result = None

        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Start process but don't wait for completion
            process = subprocess.Popen(
                cmd,
                cwd=workdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Submit process monitoring to executor
            future = executor.submit(lambda p: p.communicate(), process)

            try:
                # Wait for completion with timeout
                stdout, stderr = future.result(
                    timeout=self.timeout_config.k3s_validation if self.timeout_config else 1800
                )
                result = subprocess.CompletedProcess(
                    args=cmd,
                    returncode=process.returncode,
                    stdout=stdout,
                    stderr=stderr,
                )
            except concurrent.futures.TimeoutError:
                self.logger.error("❌ K3s validation tests timed out, cleaning up...")
                self.cleanup_on_timeout(process)
                raise subprocess.TimeoutExpired(
                    cmd=cmd,
                    timeout=self.timeout_config.k3s_validation if self.timeout_config else 1800,
                )

        if result is None:
            raise Exception("K3s validation execution failed")

        return result
