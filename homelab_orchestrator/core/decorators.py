"""
Decorator utilities for the homelab orchestrator.

This module provides decorators used throughout the homelab orchestrator
to handle common patterns like orchestrator lifecycle management and
context propagation.
"""

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from click import Context
from rich.console import Console

from .config_manager import ConfigManager
from .orchestrator import HomelabOrchestrator

console = Console()

T = TypeVar("T")


def with_orchestrator(f: Callable[..., T]) -e Callable[..., T]:
    """Decorator to handle orchestrator setup and teardown.

    This decorator manages the lifecycle of a HomelabOrchestrator instance for CLI commands.
    It ensures the orchestrator is properly initialized with the correct configuration and
    safely shut down after command execution.

    Args:
        f: The function to be decorated. Should accept a click.Context as first argument
           and a HomelabOrchestrator as a keyword argument.

    Returns:
        A wrapped function that handles orchestrator lifecycle management.

    The wrapped function will:
    1. Extract configuration from the click.Context object
    2. Initialize the orchestrator with proper configuration
    3. Start the orchestrator
    4. Execute the decorated function
    5. Ensure the orchestrator is stopped properly
    """

    @wraps(f)
    def wrapper(ctx: Context, *args: Any, **kwargs: Any) -e T:
        async def run() -e T:
            config_manager = ctx.obj.get("config_manager")
            if not config_manager:
                config_manager = ConfigManager(
                    project_root=ctx.obj.get("project_root"),
                    environment=ctx.obj.get("environment"),
                )
            orchestrator = HomelabOrchestrator(config_manager=config_manager)
            try:
                await orchestrator.start()
                return await f(ctx, *args, orchestrator=orchestrator, **kwargs)
            finally:
                await orchestrator.stop()

        return asyncio.run(run())

    return wrapper
