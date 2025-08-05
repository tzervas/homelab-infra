"""UI utilities for consistent CLI interface."""

from collections.abc import Iterator
from contextlib import contextmanager

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn


console = Console()


@contextmanager
def progress_bar(*, transient: bool = True) -> Iterator[Progress]:
    """Create a standardized progress bar with spinner and elapsed time.

    Args:
        transient: Whether the progress bar should be cleared after completion

    Returns:
        Progress context manager for use in with statement
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        transient=transient,
        console=console,
    ) as progress:
        yield progress
