#!/usr/bin/env python3
"""Pre-commit hook for warming up local caches.

This script runs before other hooks to ensure caches are properly initialized,
which helps improve the performance of subsequent pre-commit hooks.
"""

import logging
import os
import shutil
import sys
import time
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def ensure_directory(path: Path) -> None:
    """Ensure a directory exists and is writable."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        # Test write permissions by creating and removing a temp file
        test_file = path / ".write_test"
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        logger.error(f"Failed to create/verify directory {path}: {e}")
        sys.exit(1)

def warm_cache() -> None:
    """Initialize and warm up local caches for development tools."""
    project_root = Path(os.getcwd())
    cache_dirs = [
        project_root / ".mypy_cache",
        project_root / ".ruff_cache",
        project_root / ".pytest_cache",
    ]

    logger.info("Starting cache warmup process...")

    for cache_dir in cache_dirs:
        if not cache_dir.exists():
            logger.info(f"Creating cache directory: {cache_dir}")
            ensure_directory(cache_dir)
        else:
            logger.info(f"Cache directory already exists: {cache_dir}")

    # Clean any stale cache entries older than 7 days
    try:
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                for item in cache_dir.glob("**/*"):
                    if item.is_file() and (
                        item.stat().st_mtime < (time.time() - 7 * 24 * 60 * 60)
                    ):
                        item.unlink()
        logger.info("Cleaned stale cache entries")
    except Exception as e:
        logger.warning(f"Error while cleaning stale cache entries: {e}")

    logger.info("Cache warmup completed successfully")

if __name__ == "__main__":
    warm_cache()
