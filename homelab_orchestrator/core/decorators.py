import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from rich.console import Console

from .config_manager import ConfigManager
from .orchestrator import HomelabOrchestrator


console = Console()

T = TypeVar("T")


def with_orchestrator(f: Callable[..., T]) -> Callable[..., T]:
    """Decorator to handle orchestrator setup and teardown."""

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        async def run() -> T:
            config_manager = ConfigManager()
            orchestrator = HomelabOrchestrator(config_manager=config_manager)

            try:
                await orchestrator.start()
                return await f(*args, orchestrator=orchestrator, **kwargs)
            finally:
                await orchestrator.stop()

        return asyncio.run(run())

    return wrapper
