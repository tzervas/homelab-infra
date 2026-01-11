"""Secure command execution utilities."""

import logging
import shlex
import subprocess
from pathlib import Path


logger = logging.getLogger(__name__)


def validate_command(command: str | list[str], allowed_commands: list[str] | None = None) -> bool:
    """
    Validate if a command is safe to execute.

    Args:
        command: The command to validate as string or list.
        allowed_commands: Optional list of allowed command patterns.

    Returns:
        bool: True if command is safe, False otherwise.
    """
    if isinstance(command, str):
        cmd_parts = shlex.split(command)
    else:
        cmd_parts = command

    if not cmd_parts:
        logger.error("Empty command provided")
        return False

    base_cmd = Path(cmd_parts[0]).name

    # Basic security checks
    if any(c in base_cmd for c in ["&", "|", ";", ">", "<"]):
        logger.error(f"Command contains unsafe characters: {base_cmd}")
        return False

    # Check against allowed commands if provided
    if allowed_commands:
        if not any(base_cmd.startswith(allowed) for allowed in allowed_commands):
            logger.error(f"Command not in allowed list: {base_cmd}")
            return False

    return True


def execute_command_sync(
    command: str | list[str],
    check: bool = True,
    capture_output: bool = True,
    timeout: int | None = 300,
    cwd: str | None = None,
    env: dict | None = None,
    allowed_commands: list[str] | None = None,
) -> tuple[int, str, str]:
    """
    Securely execute a shell command with proper error handling and logging.

    Args:
        command: Command to execute (string or list format)
        check: Whether to raise exception on non-zero return code
        capture_output: Whether to capture stdout/stderr
        timeout: Command timeout in seconds
        cwd: Working directory for command execution
        env: Environment variables for command execution
        allowed_commands: Optional list of allowed command patterns

    Returns:
        Tuple[int, str, str]: Return code, stdout, stderr

    Raises:
        subprocess.CalledProcessError: If check=True and command returns non-zero
        subprocess.TimeoutExpired: If command exceeds timeout
        ValueError: If command validation fails
    """
    # Log command execution attempt
    cmd_str = command if isinstance(command, str) else " ".join(command)
    logger.info(f"Executing command: {cmd_str}")

    # Command validation
    if not validate_command(command, allowed_commands):
        raise ValueError(f"Command validation failed: {cmd_str}")

    try:
        # Convert string command to list if needed
        cmd_list = shlex.split(command) if isinstance(command, str) else command

        # Execute command with subprocess
        result = subprocess.run(
            cmd_list,
            shell=False,  # Avoid shell injection risks
            check=check,
            capture_output=capture_output,
            timeout=timeout,
            cwd=cwd,
            env=env,
            text=True,  # Return string output instead of bytes
        )

        # Log command result
        logger.info(f"Command completed with return code: {result.returncode}")
        if result.stdout:
            logger.debug(f"Command stdout: {result.stdout}")
        if result.stderr:
            logger.debug(f"Command stderr: {result.stderr}")

        return result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout} seconds: {cmd_str}")
        raise

    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with return code {e.returncode}: {cmd_str}")
        if e.stdout:
            logger.error(f"Command stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"Command stderr: {e.stderr}")
        raise

    except Exception:
        logger.error(f"Unexpected error executing command: {cmd_str}", exc_info=True)
        raise
