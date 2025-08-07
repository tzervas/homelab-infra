"""Async command execution utilities for homelab orchestrator."""

import asyncio
import logging
import shlex
from typing import List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

async def execute_command_async(
    command: Union[str, List[str]],
    allowed_commands: Optional[List[str]] = None,
    check: bool = True,
    timeout: Optional[float] = None,
) -> Tuple[int, str, str]:
    """Execute a shell command asynchronously with security validations.
    
    Args:
        command: Command to execute (string or list of arguments)
        allowed_commands: List of allowed command names for security
        check: If True, raises an exception on non-zero exit
        timeout: Optional timeout in seconds
        
    Returns:
        Tuple of (returncode, stdout, stderr)
    
    Raises:
        ValueError: If command validation fails
        asyncio.TimeoutError: If command times out
        subprocess.CalledProcessError: If check=True and command fails
    """
    # Convert string command to args list
    if isinstance(command, str):
        command_args = shlex.split(command)
    else:
        command_args = command

    # Validate first argument is an allowed command
    if allowed_commands:
        cmd_name = command_args[0]
        if cmd_name not in allowed_commands:
            raise ValueError(f"Command '{cmd_name}' not in allowed list: {allowed_commands}")

    # Create subprocess
    process = await asyncio.create_subprocess_exec(
        *command_args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    try:
        # Wait for completion with optional timeout
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        # Clean up process on timeout
        try:
            process.terminate()
            await asyncio.sleep(0.1)
            process.kill()
        except ProcessLookupError:
            pass
        raise

    stdout_str = stdout.decode().strip()
    stderr_str = stderr.decode().strip()

    # Log command result
    logger.debug(f"Command '{command_args[0]}' completed with code {process.returncode}")
    if stderr_str:
        logger.debug(f"stderr: {stderr_str}")

    # Handle check mode
    if check and process.returncode != 0:
        raise RuntimeError(
            f"Command '{command_args[0]}' failed with code {process.returncode}:\n"
            f"stdout: {stdout_str}\nstderr: {stderr_str}"
        )

    return process.returncode, stdout_str, stderr_str
