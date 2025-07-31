"""Main entry point for the Homelab Portal server."""

import logging
import signal
import sys
from pathlib import Path

import uvicorn
from rich.console import Console
from rich.logging import RichHandler

from homelab_orchestrator.core.config_manager import ConfigManager
from homelab_orchestrator.core.health import HealthMonitor
from homelab_orchestrator.core.security import SecurityManager

from .portal_manager import PortalManager


console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)

logger = logging.getLogger(__name__)


def run_server() -> None:
    """Run the portal server."""
    try:
        # Initialize configuration
        config_manager = ConfigManager.from_environment()
        project_root = Path.cwd()

        # Initialize managers
        health_monitor = HealthMonitor(config_manager=config_manager)
        security_manager = SecurityManager(config_manager=config_manager)

        # Create portal manager
        portal_manager = PortalManager(
            config_manager=config_manager,
            health_monitor=health_monitor,
            security_manager=security_manager,
            project_root=project_root,
        )

        # Signal handlers for graceful shutdown
        def signal_handler(sig: int, frame: any) -> None:
            logger.info("Received shutdown signal, stopping portal...")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run the server
        logger.info("Starting Homelab Portal...")
        console.print("[green]✓[/green] Portal initialized successfully")
        console.print("[blue]ℹ[/blue] Access the portal at: https://homelab.local")
        console.print("[blue]ℹ[/blue] API documentation at: https://homelab.local/docs")

        uvicorn.run(
            portal_manager.app,
            host=portal_manager.host,
            port=portal_manager.port,
            log_level="info",
            access_log=True,
            reload=False,  # Set to True for development
        )

    except KeyboardInterrupt:
        logger.info("Portal shutdown requested")
    except Exception as e:
        logger.exception(f"Failed to start portal: {e}")
        console.print(f"[red]✗[/red] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_server()
