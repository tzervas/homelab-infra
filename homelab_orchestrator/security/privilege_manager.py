"""Secure privilege management for unattended operations.

Handles secure privilege elevation with tightly scoped permissions,
secure credential handling, and environment variable isolation.
"""

from __future__ import annotations

import asyncio
import getpass
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PrivilegeContext:
    """Context for privilege escalation."""

    operation: str
    required_permissions: list[str]
    duration_limit: int = 300  # 5 minutes
    audit_required: bool = True
    environment_isolation: bool = True


class PrivilegeManager:
    """Secure privilege management for automation."""

    def __init__(self) -> None:
        """Initialize privilege manager."""
        self.logger = logging.getLogger(__name__)
        self._secure_env: dict[str, str] = {}
        self._credential_cache: dict[str, str] = {}

    async def request_privileges(
        self,
        context: PrivilegeContext,
        interactive: bool = True,
    ) -> dict[str, Any]:
        """Request elevated privileges securely.

        Args:
            context: Privilege escalation context
            interactive: Whether to allow interactive prompts

        Returns:
            Privilege grant result
        """
        self.logger.info(f"Requesting privileges for: {context.operation}")

        # Check if we already have cached credentials
        cache_key = f"{context.operation}:{hash(tuple(context.required_permissions))}"

        if cache_key in self._credential_cache:
            # Verify cached credentials are still valid
            if await self._verify_cached_credentials(cache_key):
                return {
                    "granted": True,
                    "method": "cached",
                    "expires_in": 300,  # 5 minutes
                }

        # Handle different authentication methods
        auth_methods = self._get_available_auth_methods()

        for method in auth_methods:
            try:
                if method == "sudo_nopasswd":
                    result = await self._try_sudo_nopasswd(context)
                elif method == "sudo_cached":
                    result = await self._try_sudo_cached(context)
                elif method == "interactive_sudo" and interactive:
                    result = await self._try_interactive_sudo(context)
                elif method == "keyring":
                    result = await self._try_keyring_auth(context)
                else:
                    continue

                if result.get("granted", False):
                    # Cache successful credential
                    self._credential_cache[cache_key] = method
                    return result

            except Exception as e:
                self.logger.debug(f"Auth method {method} failed: {e}")
                continue

        return {
            "granted": False,
            "error": "No valid authentication method available",
            "attempted_methods": auth_methods,
        }

    def _get_available_auth_methods(self) -> list[str]:
        """Get available authentication methods in order of preference."""
        methods = []

        # Check for passwordless sudo
        if self._check_sudo_nopasswd():
            methods.append("sudo_nopasswd")

        # Check for cached sudo credentials
        if self._check_sudo_cached():
            methods.append("sudo_cached")

        # Check for keyring integration
        if self._check_keyring_available():
            methods.append("keyring")

        # Interactive sudo as fallback
        methods.append("interactive_sudo")

        return methods

    def _check_sudo_nopasswd(self) -> bool:
        """Check if sudo is configured for passwordless operation."""
        try:
            result = subprocess.run(
                ["sudo", "-n", "true"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_sudo_cached(self) -> bool:
        """Check if sudo credentials are cached."""
        try:
            result = subprocess.run(
                ["sudo", "-n", "true"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_keyring_available(self) -> bool:
        """Check if system keyring is available."""
        try:
            import keyring

            return True
        except ImportError:
            return False

    async def _try_sudo_nopasswd(self, context: PrivilegeContext) -> dict[str, Any]:
        """Try passwordless sudo authentication."""
        try:
            process = await asyncio.create_subprocess_exec(
                "sudo",
                "-n",
                "true",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

            returncode = await process.wait()

            if returncode == 0:
                return {
                    "granted": True,
                    "method": "sudo_nopasswd",
                    "expires_in": 900,  # 15 minutes typical sudo timeout
                }
            return {"granted": False, "error": "Passwordless sudo not configured"}

        except Exception as e:
            return {"granted": False, "error": f"Sudo test failed: {e}"}

    async def _try_sudo_cached(self, context: PrivilegeContext) -> dict[str, Any]:
        """Try cached sudo credentials."""
        return await self._try_sudo_nopasswd(context)  # Same test

    async def _try_interactive_sudo(self, context: PrivilegeContext) -> dict[str, Any]:
        """Try interactive sudo authentication."""
        if not sys.stdin.isatty():
            return {"granted": False, "error": "No TTY available for interactive sudo"}

        try:
            # Get password securely
            password = getpass.getpass(
                f"[SUDO] Password required for {context.operation}: ",
            )

            if not password:
                return {"granted": False, "error": "No password provided"}

            # Test sudo with password
            process = await asyncio.create_subprocess_exec(
                "sudo",
                "-S",
                "true",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate(input=f"{password}\n".encode())

            # Clear password from memory
            password = "x" * len(password)
            del password

            if process.returncode == 0:
                return {
                    "granted": True,
                    "method": "interactive_sudo",
                    "expires_in": 900,
                }
            return {"granted": False, "error": "Authentication failed"}

        except Exception as e:
            return {"granted": False, "error": f"Interactive sudo failed: {e}"}

    async def _try_keyring_auth(self, context: PrivilegeContext) -> dict[str, Any]:
        """Try keyring-based authentication."""
        try:
            import keyring

            service_name = "homelab-orchestrator"
            username = getpass.getuser()

            password = keyring.get_password(service_name, username)
            if not password:
                return {"granted": False, "error": "No credentials in keyring"}

            # Test sudo with keyring password
            process = await asyncio.create_subprocess_exec(
                "sudo",
                "-S",
                "true",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate(input=f"{password}\n".encode())

            if process.returncode == 0:
                return {
                    "granted": True,
                    "method": "keyring",
                    "expires_in": 900,
                }
            return {"granted": False, "error": "Keyring authentication failed"}

        except ImportError:
            return {"granted": False, "error": "Keyring module not available"}
        except Exception as e:
            return {"granted": False, "error": f"Keyring auth failed: {e}"}

    async def _verify_cached_credentials(self, cache_key: str) -> bool:
        """Verify cached credentials are still valid."""
        try:
            process = await asyncio.create_subprocess_exec(
                "sudo",
                "-n",
                "true",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

            returncode = await process.wait()
            return returncode == 0

        except Exception:
            return False

    async def execute_privileged_command(
        self,
        command: list[str],
        context: PrivilegeContext,
        timeout: int = 300,
    ) -> dict[str, Any]:
        """Execute command with elevated privileges.

        Args:
            command: Command and arguments to execute
            context: Privilege context
            timeout: Command timeout in seconds

        Returns:
            Command execution result
        """
        # Request privileges first
        auth_result = await self.request_privileges(context, interactive=False)

        if not auth_result.get("granted", False):
            return {
                "success": False,
                "error": "Privilege escalation failed",
                "details": auth_result,
            }

        # Create isolated environment
        secure_env = self._create_secure_environment() if context.environment_isolation else None

        try:
            # Prepend sudo to command
            privileged_command = ["sudo", *command]

            # Execute with isolation
            if secure_env:
                process = await asyncio.create_subprocess_exec(
                    *privileged_command,
                    env=secure_env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    *privileged_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )

                return {
                    "success": process.returncode == 0,
                    "returncode": process.returncode,
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "command": " ".join(command),
                    "method": auth_result.get("method"),
                }

            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                await process.wait()

                return {
                    "success": False,
                    "error": f"Command timed out after {timeout} seconds",
                    "command": " ".join(command),
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Command execution failed: {e}",
                "command": " ".join(command),
            }

        finally:
            # Audit the privileged operation
            if context.audit_required:
                self._audit_privileged_operation(command, context, auth_result)

    def _create_secure_environment(self) -> dict[str, str]:
        """Create secure isolated environment variables."""
        # Start with minimal safe environment
        secure_env = {
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "HOME": os.path.expanduser("~"),
            "USER": getpass.getuser(),
            "LOGNAME": getpass.getuser(),
            "SHELL": os.environ.get("SHELL", "/bin/bash"),
            "TERM": os.environ.get("TERM", "xterm"),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": "C.UTF-8",
        }

        # Add specific homelab variables if needed
        homelab_vars = [
            "HOMELAB_ENVIRONMENT",
            "HOMELAB_CLUSTER_TYPE",
            "HOMELAB_PROJECT_ROOT",
            "KUBECONFIG",
        ]

        for var in homelab_vars:
            if var in os.environ:
                secure_env[var] = os.environ[var]

        return secure_env

    def _audit_privileged_operation(
        self,
        command: list[str],
        context: PrivilegeContext,
        auth_result: dict[str, Any],
    ) -> None:
        """Audit privileged operation for security monitoring."""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": getpass.getuser(),
            "operation": context.operation,
            "command": " ".join(command),
            "auth_method": auth_result.get("method"),
            "required_permissions": context.required_permissions,
        }

        # Log to secure audit log
        self.logger.info(f"PRIVILEGED_OPERATION: {audit_entry}")

        # Could also send to external audit system
        try:
            audit_file = Path("/var/log/homelab/privileged-operations.log")
            audit_file.parent.mkdir(parents=True, exist_ok=True)

            with open(audit_file, "a") as f:
                import json

                f.write(json.dumps(audit_entry) + "\n")

        except Exception as e:
            self.logger.warning(f"Failed to write audit log: {e}")

    def store_credential_securely(self, service: str, credential: str) -> bool:
        """Store credential in system keyring securely.

        Args:
            service: Service identifier
            credential: Credential to store

        Returns:
            True if stored successfully
        """
        try:
            import keyring

            username = getpass.getuser()
            keyring.set_password(f"homelab-{service}", username, credential)

            return True

        except ImportError:
            self.logger.warning("Keyring not available for credential storage")
            return False
        except Exception as e:
            self.logger.exception(f"Failed to store credential: {e}")
            return False

    def clear_credential_cache(self) -> None:
        """Clear cached credentials for security."""
        self._credential_cache.clear()
        self.logger.info("Credential cache cleared")

    def __del__(self) -> None:
        """Cleanup on destruction."""
        self.clear_credential_cache()
