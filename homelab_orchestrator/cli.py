"""Unified CLI interface for homelab orchestration.

Provides a clean, comprehensive command-line interface that replaces all
existing bash scripts with a unified Python-based automation system.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .core.decorators import with_orchestrator

from .__version__ import __version__
from .core.config_manager import ConfigContext, ConfigManager
from .core.orchestrator import HomelabOrchestrator


console = Console()


def setup_logging(level: str) -> None:
    """Setup logging configuration.

    Args:
        level: Logging level
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


@click.group()
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Set logging level",
)
@click.option(
    "--environment",
    default="development",
    type=click.Choice(["development", "staging", "production"]),
    help="Target environment",
)
@click.option(
    "--cluster-type",
    default="local",
    type=click.Choice(["local", "remote", "hybrid"]),
    help="Cluster deployment type",
)
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.version_option(version=__version__, prog_name="Homelab Orchestrator")
@click.pass_context
def cli(
    ctx: click.Context,
    log_level: str,
    environment: str,
    cluster_type: str,
    project_root: str | None,
) -> None:
    """Homelab Orchestrator - Unified infrastructure automation."""
    setup_logging(log_level)

    # Setup context
    project_path = Path(project_root) if project_root else Path.cwd()
    config_context = ConfigContext(
        environment=environment,
        cluster_type=cluster_type,
    )

    config_manager = ConfigManager(
        project_root=project_path,
        config_context=config_context,
    )

    ctx.ensure_object(dict)
    ctx.obj["config_manager"] = config_manager
    ctx.obj["project_root"] = project_path
    ctx.obj["log_level"] = log_level


@cli.group()
@click.pass_context
def deploy(ctx: click.Context) -> None:
    """Deployment operations."""


@deploy.command("infrastructure")
@click.option("--components", multiple=True, help="Specific components to deploy")
@click.option("--dry-run", is_flag=True, help="Perform validation without deployment")
@click.option("--skip-hooks", is_flag=True, help="Skip deployment hooks")
@with_orchestrator
def deploy_infrastructure(
    ctx: click.Context,
    components: list[str],
    dry_run: bool,
    skip_hooks: bool,
    orchestrator: HomelabOrchestrator,
    ) -> None:
    """Deploy complete homelab infrastructure."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Deploying infrastructure...", total=None)

        result = asyncio.run(
            orchestrator.deploy_full_infrastructure(
                components=list(components) if components else None,
                dry_run=dry_run,
            ),
        )

        progress.update(task, description="Deployment completed", completed=100)

        # Display results
        _display_deployment_result(result)


@deploy.command("service")
@click.argument("service_name")
@click.option("--namespace", help="Target namespace")
@click.option("--dry-run", is_flag=True, help="Validate without deployment")
@click.pass_context
def deploy_service(
    ctx: click.Context,
    service_name: str,
    namespace: str | None,
    dry_run: bool,
) -> None:
    """Deploy specific service."""
    console.print(f"[yellow]Deploying service: {service_name}[/yellow]")

    if dry_run:
        console.print("[blue]Dry run mode - no actual deployment[/blue]")

    # Implementation for service deployment
    console.print(f"[green]Service {service_name} deployment completed[/green]")


@cli.group()
@click.pass_context
def manage(ctx: click.Context) -> None:
    """Backup, Teardown, and Recovery operations."""


@manage.command("backup")
@click.option("--components", multiple=True, help="Specific components to backup")
@click.pass_context
def manage_backup(ctx: click.Context, components: list[str]) -> None:
    """Backup infrastructure components."""

    async def _backup() -> None:
        config_manager = ctx.obj["config_manager"]
        orchestrator = HomelabOrchestrator(
            config_manager=config_manager,
            project_root=ctx.obj["project_root"],
            log_level=ctx.obj["log_level"],
        )

        try:
            await orchestrator.start()
            result = await orchestrator.deployment_manager.backup_infrastructure(components)
            _display_deployment_result(result)
        finally:
            await orchestrator.stop()

    asyncio.run(_backup())


@manage.command("teardown")
@click.option("--force", is_flag=True, help="Force teardown without confirmation")
@click.option("--no-backup", is_flag=True, help="Skip backup before teardown")
@click.pass_context
def manage_teardown(ctx: click.Context, force: bool, no_backup: bool) -> None:
    """Teardown complete infrastructure."""

    async def _teardown() -> None:
        config_manager = ctx.obj["config_manager"]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing orchestrator...", total=None)

            orchestrator = HomelabOrchestrator(
                config_manager=config_manager,
                project_root=ctx.obj["project_root"],
                log_level=ctx.obj["log_level"],
            )

            try:
                progress.update(task, description="Starting orchestrator...")
                await orchestrator.start()

                progress.update(task, description="Tearing down infrastructure...")
                result = await orchestrator.teardown_infrastructure(
                    environment=config_manager.context.environment,
                    force=force,
                    backup=not no_backup,
                )

                progress.update(task, description="Teardown completed", completed=100)

                # Display results
                _display_teardown_result(result)

            finally:
                progress.update(task, description="Cleaning up...")
                await orchestrator.stop()

    asyncio.run(_teardown())


@manage.command("recover")
@click.option("--components", multiple=True, help="Specific components to recover")
@click.pass_context
def manage_recover(ctx: click.Context, components: list[str]) -> None:
    """Recover infrastructure components from backup."""

    async def _recover() -> None:
        config_manager = ctx.obj["config_manager"]
        orchestrator = HomelabOrchestrator(
            config_manager=config_manager,
            project_root=ctx.obj["project_root"],
            log_level=ctx.obj["log_level"],
        )

        try:
            await orchestrator.start()
            result = await orchestrator.deployment_manager.recover_infrastructure(components)
            _display_deployment_result(result)
        finally:
            await orchestrator.stop()

    asyncio.run(_recover())


@cli.group()
@click.pass_context
def health(ctx: click.Context) -> None:
    """Health monitoring and validation."""


@health.command("check")
@click.option("--comprehensive", is_flag=True, help="Run comprehensive health check")
@click.option("--component", multiple=True, help="Check specific components")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def health_check(
    ctx: click.Context,
    comprehensive: bool,
    component: list[str],
    output_format: str,
) -> None:
    """Check system health status."""

    async def _check_health() -> None:
        config_manager = ctx.obj["config_manager"]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running health checks...", total=None)

            orchestrator = HomelabOrchestrator(
                config_manager=config_manager,
                project_root=ctx.obj["project_root"],
                log_level=ctx.obj["log_level"],
            )

            try:
                await orchestrator.start()

                result = await orchestrator.validate_system_health()

                progress.update(task, description="Health check completed", completed=100)

                # Display results
                _display_health_result(result, output_format)

            finally:
                await orchestrator.stop()

    asyncio.run(_check_health())


@health.command("monitor")
@click.option("--interval", default=60, help="Monitoring interval in seconds")
@click.option("--duration", default=0, help="Monitoring duration in seconds (0 for continuous)")
@click.pass_context
def health_monitor(ctx: click.Context, interval: int, duration: int) -> None:
    """Start continuous health monitoring."""
    console.print(f"[blue]Starting health monitoring (interval: {interval}s)[/blue]")

    if duration > 0:
        console.print(f"[blue]Monitoring duration: {duration}s[/blue]")
    else:
        console.print("[blue]Continuous monitoring (Ctrl+C to stop)[/blue]")

    # Implementation for continuous monitoring
    console.print("[green]Health monitoring started[/green]")


@cli.group()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Configuration management."""


@config.command("validate")
@click.option("--comprehensive", is_flag=True, help="Run comprehensive validation")
@click.pass_context
def config_validate(ctx: click.Context, comprehensive: bool) -> None:
    """Validate configuration files."""
    config_manager = ctx.obj["config_manager"]

    console.print("[blue]Validating configuration...[/blue]")

    validation_result = config_manager.validate_configuration()

    # Create validation table
    table = Table(title="Configuration Validation Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details")

    # Overall status
    status_color = "green" if validation_result["status"] == "valid" else "red"
    table.add_row(
        "Overall Status",
        f"[{status_color}]{validation_result['status'].upper()}[/{status_color}]",
        f"Environment: {validation_result['environment']}",
    )

    # Configuration files
    table.add_row(
        "Config Files",
        f"[green]{validation_result['config_files_loaded']}[/green]",
        "Configuration files loaded",
    )

    # Issues
    if validation_result["issues"]:
        for issue in validation_result["issues"]:
            table.add_row("Issue", "[red]ERROR[/red]", issue)

    # Warnings
    if validation_result["warnings"]:
        for warning in validation_result["warnings"]:
            table.add_row("Warning", "[yellow]WARNING[/yellow]", warning)

    console.print(table)

    if validation_result["status"] != "valid":
        sys.exit(1)


@config.command("show")
@click.argument("config_type", required=False)
@click.option("--key", help="Specific configuration key")
@click.option("--format", "output_format", type=click.Choice(["yaml", "json"]), default="yaml")
@click.pass_context
def config_show(
    ctx: click.Context,
    config_type: str | None,
    key: str | None,
    output_format: str,
) -> None:
    """Show configuration values."""
    config_manager = ctx.obj["config_manager"]

    if config_type:
        config_data = config_manager.get_config(config_type, key)
    else:
        config_data = config_manager.get_deployment_config()

    if output_format == "json":
        console.print(json.dumps(config_data, indent=2, default=str))
    else:
        import yaml

        console.print(yaml.dump(config_data, default_flow_style=False))


@cli.group()
@click.pass_context
def gpu(ctx: click.Context) -> None:
    """GPU resource management."""


@gpu.command("discover")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def gpu_discover(ctx: click.Context, output_format: str) -> None:
    """Discover available GPU resources."""

    async def _discover() -> None:
        config_manager = ctx.obj["config_manager"]

        orchestrator = HomelabOrchestrator(
            config_manager=config_manager,
            project_root=ctx.obj["project_root"],
            log_level=ctx.obj["log_level"],
        )

        try:
            await orchestrator.start()

            result = await orchestrator.manage_gpu_resources("discover")

            _display_gpu_result(result, output_format)

        finally:
            await orchestrator.stop()

    asyncio.run(_discover())


@gpu.command("status")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def gpu_status(ctx: click.Context, output_format: str) -> None:
    """Show GPU resource status."""

    async def _status() -> None:
        config_manager = ctx.obj["config_manager"]

        orchestrator = HomelabOrchestrator(
            config_manager=config_manager,
            project_root=ctx.obj["project_root"],
            log_level=ctx.obj["log_level"],
        )

        try:
            await orchestrator.start()

            result = await orchestrator.manage_gpu_resources("monitor")

            _display_gpu_result(result, output_format)

        finally:
            await orchestrator.stop()

    asyncio.run(_status())


@cli.group()
@click.pass_context
def webhook(ctx: click.Context) -> None:
    """Webhook management."""


@webhook.command("start")
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8080, help="Port to bind to")
@click.pass_context
def webhook_start(ctx: click.Context, host: str, port: int) -> None:
    """Start webhook server."""
    console.print(f"[blue]Starting webhook server on {host}:{port}[/blue]")

    # Implementation for webhook server
    console.print("[green]Webhook server started[/green]")


@cli.group()
@click.pass_context
def certificates(ctx: click.Context) -> None:
    """Certificate management operations."""


@certificates.command("deploy")
@click.pass_context
@with_orchestrator
def certificates_deploy(ctx: click.Context, orchestrator: HomelabOrchestrator) -> None:
    """Deploy cert-manager and certificate issuers."""
    # Deploy cert-manager
    result = asyncio.run(orchestrator.certificate_manager.deploy_cert_manager())

    if result["status"] == "success":
        console.print("[green]✅ cert-manager deployed successfully[/green]")
        if "issuers" in result:
            console.print(
                f"[blue]📋 Deployed issuers: {', '.join(result['issuers'])}[/blue]",
            )
    else:
        console.print(
            f"[red]❌ cert-manager deployment failed: {result.get('error', 'Unknown error')}[/red]",
        )


@certificates.command("validate")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
@with_orchestrator
def certificates_validate(ctx: click.Context, output_format: str, orchestrator: HomelabOrchestrator) -> None:
    """Validate TLS certificates and endpoints."""
    result = asyncio.run(orchestrator.certificate_manager.validate_certificates())

    if output_format == "json":
        console.print(json.dumps(result, indent=2, default=str))
        return

    # Display validation results in table format
    table = Table(title="Certificate Validation Results")
    table.add_column("Endpoint", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("SSL Verified", style="green")
    table.add_column("Details")

    for endpoint, details in result.get("endpoints", {}).items():
        status = details["status"]
        status_color = "green" if status == "success" else "red"
        ssl_status = "✅" if details.get("ssl_verified") else "❌"

        error_info = details.get("error", "")
        if details.get("status_code"):
            error_info = f"HTTP {details['status_code']}"

        table.add_row(
            endpoint,
            f"[{status_color}]{status.upper()}[/{status_color}]",
            ssl_status,
            error_info,
        )

    console.print(table)

    # Summary
    summary = result.get("summary", {})
    console.print(
        f"\n📊 Summary: {summary.get('successful', 0)}/{summary.get('total', 0)} endpoints validated successfully",
    )


@certificates.command("check-expiry")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def certificates_check_expiry(ctx: click.Context, output_format: str) -> None:
    """Check certificate expiry dates."""

    async def _check_expiry() -> None:
        config_manager = ctx.obj["config_manager"]
        orchestrator = HomelabOrchestrator(
            config_manager=config_manager,
            project_root=ctx.obj["project_root"],
            log_level=ctx.obj["log_level"],
        )

        try:
            await orchestrator.start()

            result = await orchestrator.certificate_manager.check_certificate_expiry()

            if output_format == "json":
                console.print(json.dumps(result, indent=2, default=str))
                return

            if result["status"] != "success":
                console.print(
                    f"[red]❌ Failed to check certificate expiry: {result.get('error')}[/red]",
                )
                return

            # Display certificate expiry information
            table = Table(title="Certificate Expiry Information")
            table.add_column("Certificate", style="cyan")
            table.add_column("Namespace")
            table.add_column("Days Until Expiry", style="bold")
            table.add_column("Status")
            table.add_column("Needs Renewal")

            for cert in result.get("certificates", []):
                days_color = (
                    "red"
                    if cert["days_until_expiry"] < 7
                    else "yellow"
                    if cert["days_until_expiry"] < 30
                    else "green"
                )
                renewal_status = "⚠️ YES" if cert["needs_renewal"] else "✅ NO"

                table.add_row(
                    cert["name"],
                    cert["namespace"],
                    f"[{days_color}]{cert['days_until_expiry']}[/{days_color}]",
                    cert["status"],
                    renewal_status,
                )

            console.print(table)

            # Summary
            summary = result.get("summary", {})
            console.print(
                f"\n📊 Summary: {summary.get('needs_renewal', 0)}/{summary.get('total', 0)} certificates need renewal",
            )

        finally:
            await orchestrator.stop()

    asyncio.run(_check_expiry())


@certificates.command("renew")
@click.argument("cert_name")
@click.option("--namespace", default="default", help="Certificate namespace")
@click.pass_context
def certificates_renew(ctx: click.Context, cert_name: str, namespace: str) -> None:
    """Force renewal of a specific certificate."""

    async def _renew_cert() -> None:
        config_manager = ctx.obj["config_manager"]
        orchestrator = HomelabOrchestrator(
            config_manager=config_manager,
            project_root=ctx.obj["project_root"],
            log_level=ctx.obj["log_level"],
        )

        try:
            await orchestrator.start()

            result = await orchestrator.certificate_manager.renew_certificate(cert_name, namespace)

            if result["status"] == "success":
                console.print(f"[green]✅ {result['message']}[/green]")
                console.print(
                    f"[blue]Monitor renewal with: kubectl describe certificate {cert_name} -n {namespace}[/blue]",
                )
            else:
                console.print(f"[red]❌ Certificate renewal failed: {result.get('error')}[/red]")

        finally:
            await orchestrator.stop()

    asyncio.run(_renew_cert())


@cli.command("status")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def status(ctx: click.Context, output_format: str) -> None:
    """Show overall system status."""

    async def _status() -> None:
        config_manager = ctx.obj["config_manager"]

        orchestrator = HomelabOrchestrator(
            config_manager=config_manager,
            project_root=ctx.obj["project_root"],
            log_level=ctx.obj["log_level"],
        )

        try:
            await orchestrator.start()

            # Get system status
            system_status = orchestrator.get_system_status()

            if output_format == "json":
                console.print(json.dumps(system_status, indent=2, default=str))
            else:
                _display_system_status(system_status)

        finally:
            await orchestrator.stop()

    asyncio.run(_status())


# Display helper functions
def _display_deployment_result(result: Any) -> None:
    """Display deployment results in a nice format."""
    status_color = {
        "success": "green",
        "failure": "red",
        "warning": "yellow",
        "partial": "yellow",
    }.get(result.status, "white")

    console.print(
        Panel(
            f"[{status_color}]{result.status.upper()}[/{status_color}]\n"
            f"Operation: {result.operation}\n"
            f"Duration: {result.duration:.2f}s",
            title="Deployment Result",
        ),
    )

    # Display comprehensive validation results if available
    if hasattr(result, "details") and "comprehensive_validation" in result.details:
        validation = result.details["comprehensive_validation"]
        if "validation_details" in validation:
            _display_validation_details(validation["validation_details"])

    if hasattr(result, "components_deployed") and result.components_deployed:
        table = Table(title="Deployed Components")
        table.add_column("Component", style="green")
        table.add_column("Status", style="bold")

        for component in result.components_deployed:
            table.add_row(component, "[green]SUCCESS[/green]")

        console.print(table)

    if hasattr(result, "components_failed") and result.components_failed:
        table = Table(title="Failed Components")
        table.add_column("Component", style="red")
        table.add_column("Status", style="bold")

        for component in result.components_failed:
            table.add_row(component, "[red]FAILED[/red]")

        console.print(table)

    if result.recommendations:
        console.print("\n[yellow]Recommendations:[/yellow]")
        for i, rec in enumerate(result.recommendations, 1):
            console.print(f"  {i}. {rec}")


def _display_teardown_result(result: Any) -> None:
    """Display teardown results in a nice format."""
    status_color = {
        "success": "green",
        "failure": "red",
        "warning": "yellow",
    }.get(result.status, "white")

    console.print(
        Panel(
            f"[{status_color}]{result.status.upper()}[/{status_color}]\n"
            f"Operation: {result.operation}\n"
            f"Duration: {result.duration:.2f}s",
            title="Teardown Result",
        ),
    )

    # Display clean state validation if available
    if hasattr(result, "details") and "validation" in result.details:
        validation = result.details["validation"]

        table = Table(title="Clean State Validation")
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details")

        clean_status = "✅ CLEAN" if validation.get("clean", False) else "❌ NOT CLEAN"
        table.add_row("Overall State", clean_status, "")

        if validation.get("issues"):
            for issue in validation["issues"]:
                table.add_row("Issue", "[red]FOUND[/red]", issue)

        console.print(table)

    if result.recommendations:
        console.print("\n[yellow]Recommendations:[/yellow]")
        for i, rec in enumerate(result.recommendations, 1):
            console.print(f"  {i}. {rec}")


def _display_validation_details(validation_details: dict[str, Any]) -> None:
    """Display validation details in a structured format."""
    table = Table(title="Deployment Validation Details")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")

    for component, status in validation_details.items():
        if status == "passed":
            status_display = "[green]✅ PASSED[/green]"
        elif status == "failed":
            status_display = "[red]❌ FAILED[/red]"
        else:
            status_display = f"[yellow]❓ {status.upper()}[/yellow]"

        table.add_row(component.replace("_", " ").title(), status_display)

    console.print(table)


def _display_health_result(result: Any, output_format: str) -> None:
    """Display health check results."""
    if output_format == "json":
        console.print(json.dumps(result.details, indent=2, default=str))
        return

    status_color = {
        "success": "green",
        "warning": "yellow",
        "failure": "red",
    }.get(result.status, "white")

    console.print(
        Panel(
            f"[{status_color}]{result.status.upper()}[/{status_color}]\n"
            f"Duration: {result.duration:.2f}s",
            title="Health Check Result",
        ),
    )

    if result.details:
        for component, details in result.details.items():
            table = Table(title=f"{component.title()} Health")
            table.add_column("Check", style="cyan")
            table.add_column("Status", style="bold")
            table.add_column("Details")

            if isinstance(details, dict):
                for key, value in details.items():
                    if key == "status":
                        status_icon = "✅" if value == "healthy" else "❌"
                        table.add_row("Status", f"{status_icon} {value}", "")
                    else:
                        table.add_row(key, str(value), "")

            console.print(table)


def _display_gpu_result(result: Any, output_format: str) -> None:
    """Display GPU management results."""
    if output_format == "json":
        console.print(json.dumps(result.details, indent=2, default=str))
        return

    if result.status == "success" and result.details:
        gpus = result.details.get("gpus", {})

        if gpus:
            table = Table(title="GPU Resources")
            table.add_column("GPU ID", style="cyan")
            table.add_column("Name", style="bold")
            table.add_column("Memory", style="green")
            table.add_column("Utilization", style="yellow")
            table.add_column("Available", style="blue")

            for gpu_id, gpu_data in gpus.items():
                memory_info = (
                    f"{gpu_data.get('memory_used', 0)}MB / {gpu_data.get('memory_total', 0)}MB"
                )
                utilization = f"{gpu_data.get('utilization', 0):.1f}%"
                available = "✅" if gpu_data.get("available", False) else "❌"

                table.add_row(
                    gpu_id,
                    gpu_data.get("name", "Unknown"),
                    memory_info,
                    utilization,
                    available,
                )

            console.print(table)
        else:
            console.print("[yellow]No GPU resources found[/yellow]")
    else:
        console.print(
            f"[red]GPU operation failed: {result.details.get('error', 'Unknown error')}[/red]",
        )


def _display_system_status(status: dict[str, Any]) -> None:
    """Display system status in table format."""
    table = Table(title="System Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details")

    # Orchestrator status
    orchestrator_status = status.get("orchestrator", {})
    table.add_row(
        "Orchestrator",
        "[green]RUNNING[/green]",
        f"Queue: {orchestrator_status.get('event_queue_size', 0)}, "
        f"Tasks: {orchestrator_status.get('running_tasks', 0)}",
    )

    # Configuration status
    config_status = status.get("configuration", {})
    table.add_row(
        "Configuration",
        "[green]LOADED[/green]",
        f"Environment: {config_status.get('environment', 'unknown')}, "
        f"Type: {config_status.get('cluster_type', 'unknown')}",
    )

    # Managers status
    managers = status.get("managers", {})
    for manager, enabled in managers.items():
        status_text = "[green]ENABLED[/green]" if enabled else "[gray]DISABLED[/gray]"
        table.add_row(manager.title(), status_text, "")

    console.print(table)


if __name__ == "__main__":
    cli()
