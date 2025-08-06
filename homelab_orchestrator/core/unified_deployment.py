"""Unified deployment orchestration.

Replaces all bash deployment scripts with Python-based deployment steps.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console


@dataclass
class DeploymentStep:
    """Represents a single deployment step."""

    name: str
    description: str
    command: str | None = None
    function: Callable | None = None
    dependencies: list[str] = field(default_factory=list)
    timeout: int = 300
    critical: bool = True
