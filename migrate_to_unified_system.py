#!/usr/bin/env python3
"""Migration script to transition from legacy scripts to unified orchestration system.

This script validates the new unified system, performs comprehensive testing,
and safely removes legacy scripts once the new system is proven to work.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


try:
    import yaml
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please install: pip install pyyaml rich")
    sys.exit(1)


console = Console()
logger = logging.getLogger(__name__)


class MigrationValidator:
    """Comprehensive migration validation and testing."""

    def __init__(self, project_root: Path) -> None:
        """Initialize migration validator.

        Args:
            project_root: Path to project root directory
        """
        self.project_root = project_root
        self.backup_dir = (
            project_root / "legacy_backup" / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(project_root / "migration.log"),
            ],
        )

    async def run_migration_validation(self) -> dict[str, Any]:
        """Run comprehensive migration validation.

        Returns:
            Migration validation results
        """
        console.print(Panel("[bold blue]Homelab Unified System Migration Validator[/bold blue]"))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Phase 1: Validate unified system
            task = progress.add_task("Validating unified orchestration system...", total=None)

            validation_result = await self._validate_unified_system()
            if not validation_result["success"]:
                console.print("[red]❌ Unified system validation failed[/red]")
                return validation_result

            progress.update(task, description="✅ Unified system validated")

            # Phase 2: Test critical workflows
            progress.update(task, description="Testing critical workflows...")

            workflow_result = await self._test_critical_workflows()
            if not workflow_result["success"]:
                console.print("[red]❌ Critical workflow testing failed[/red]")
                return workflow_result

            progress.update(task, description="✅ Critical workflows tested")

            # Phase 3: Validate configuration migration
            progress.update(task, description="Validating configuration migration...")

            config_result = await self._validate_configuration_migration()
            if not config_result["success"]:
                console.print("[red]❌ Configuration migration validation failed[/red]")
                return config_result

            progress.update(task, description="✅ Configuration migration validated")

            # Phase 4: Compare functionality
            progress.update(task, description="Comparing functionality with legacy scripts...")

            comparison_result = await self._compare_functionality()

            progress.update(task, description="✅ Functionality comparison completed")

            # Phase 5: Security validation
            progress.update(task, description="Validating security posture...")

            security_result = await self._validate_security_posture()

            progress.update(task, description="✅ Security validation completed", completed=100)

        # Consolidate results
        overall_success = all(
            [
                validation_result["success"],
                workflow_result["success"],
                config_result["success"],
                comparison_result["success"],
                security_result["success"],
            ],
        )

        overall_result = {
            "success": overall_success,
            "validation_phases": {
                "unified_system": validation_result,
                "critical_workflows": workflow_result,
                "configuration_migration": config_result,
                "functionality_comparison": comparison_result,
                "security_validation": security_result,
            },
            "timestamp": datetime.now().isoformat(),
            "migration_ready": overall_success,  # Set based on overall success
        }

        # Log validation results
        if overall_result["success"]:
            console.print("[green]✅ All validation phases passed[/green]")
        else:
            console.print("[red]❌ Some validation phases failed[/red]")

        return overall_result

    async def _validate_unified_system(self) -> dict[str, Any]:
        """Validate the unified orchestration system."""
        try:
            # Initialize configuration manager
            try:
                from homelab_orchestrator.core.config_manager import ConfigContext, ConfigManager
                from homelab_orchestrator.core.orchestrator import HomelabOrchestrator
                from homelab_orchestrator.validation.validator import SystemValidator
            except ImportError as e:
                return {
                    "success": False,
                    "error": f"Cannot import unified system modules: {e}",
                }

            config_context = ConfigContext(
                environment="development",
                cluster_type="local",
            )

            config_manager = ConfigManager(
                project_root=self.project_root,
                config_context=config_context,
            )

            # Validate configuration
            config_validation = config_manager.validate_configuration()
            if config_validation["status"] != "valid":
                return {
                    "success": False,
                    "error": "Configuration validation failed",
                    "details": config_validation,
                }

            # Initialize orchestrator
            orchestrator = HomelabOrchestrator(
                config_manager=config_manager,
                project_root=self.project_root,
                log_level="INFO",
            )

            try:
                # Start orchestrator
                await orchestrator.start()

                # Get system status
                system_status = orchestrator.get_system_status()

                # Validate all managers are initialized
                managers = system_status.get("managers", {})
                required_managers = ["deployment", "health", "security", "webhook"]

                missing_managers = [m for m in required_managers if not managers.get(m, False)]
                if missing_managers:
                    return {
                        "success": False,
                        "error": f"Missing required managers: {missing_managers}",
                        "details": system_status,
                    }

                return {
                    "success": True,
                    "message": "Unified system validation passed",
                    "managers_initialized": len([m for m in managers.values() if m]),
                    "system_status": system_status,
                }

            finally:
                await orchestrator.stop()

        except Exception as e:
            logger.exception(f"Unified system validation failed: {e}")
            return {
                "success": False,
                "error": f"System validation failed: {e}",
            }

    async def _test_critical_workflows(self) -> dict[str, Any]:
        """Test critical deployment and management workflows."""
        try:
            from homelab_orchestrator.core.config_manager import ConfigContext, ConfigManager
            from homelab_orchestrator.core.orchestrator import HomelabOrchestrator
            from homelab_orchestrator.validation.validator import SystemValidator

            config_context = ConfigContext(environment="development")
            config_manager = ConfigManager(
                project_root=self.project_root,
                config_context=config_context,
            )

            orchestrator = HomelabOrchestrator(
                config_manager=config_manager,
                project_root=self.project_root,
                log_level="INFO",
            )

            try:
                await orchestrator.start()

                workflow_results = {}

                # Test 1: Dry-run infrastructure deployment
                deploy_result = await orchestrator.deploy_full_infrastructure(
                    environment="development",
                    dry_run=True,
                )

                workflow_results["infrastructure_dry_run"] = {
                    "success": deploy_result.status in ["success", "warning"],
                    "status": deploy_result.status,
                    "duration": deploy_result.duration,
                }

                # Test 2: System health validation
                health_result = await orchestrator.validate_system_health()

                workflow_results["health_validation"] = {
                    "success": health_result.status in ["success", "warning"],
                    "status": health_result.status,
                    "duration": health_result.duration,
                }

                # Test 3: Configuration management
                system_validator = SystemValidator(config_manager)
                validation_suite = await system_validator.run_comprehensive_validation()

                workflow_results["comprehensive_validation"] = {
                    "success": validation_suite.overall_status in ["pass", "warning"],
                    "status": validation_suite.overall_status,
                    "tests_run": len(validation_suite.results),
                    "duration": validation_suite.duration,
                }

                # Determine overall success
                all_success = all(result["success"] for result in workflow_results.values())

                return {
                    "success": all_success,
                    "message": "Critical workflows tested",
                    "workflow_results": workflow_results,
                }

            finally:
                await orchestrator.stop()

        except Exception as e:
            logger.exception(f"Critical workflow testing failed: {e}")
            return {
                "success": False,
                "error": f"Workflow testing failed: {e}",
            }

    async def _validate_configuration_migration(self) -> dict[str, Any]:
        """Validate that consolidated configuration covers all use cases."""
        try:
            # Check consolidated configuration completeness
            consolidated_dir = self.project_root / "config" / "consolidated"

            required_configs = [
                "domains.yaml",
                "networking.yaml",
                "storage.yaml",
                "security.yaml",
                "resources.yaml",
                "namespaces.yaml",
                "environments.yaml",
                "services.yaml",
            ]

            missing_configs = []
            for config_file in required_configs:
                config_path = consolidated_dir / config_file
                if not config_path.exists():
                    missing_configs.append(config_file)

            if missing_configs:
                return {
                    "success": False,
                    "error": f"Missing consolidated config files: {missing_configs}",
                }

            # Validate configuration can be loaded
            from homelab_orchestrator.core.config_manager import ConfigManager

            config_manager = ConfigManager.from_environment()

            # Test loading all configuration types
            config_types = [
                "domains",
                "networking",
                "storage",
                "security",
                "resources",
                "namespaces",
                "services",
            ]
            loaded_configs = {}

            for config_type in config_types:
                try:
                    config_data = config_manager.get_config(config_type)
                    loaded_configs[config_type] = bool(config_data)
                except Exception as e:
                    loaded_configs[config_type] = False
                    logger.warning(f"Failed to load {config_type} config: {e}")

            success_count = sum(loaded_configs.values())

            return {
                "success": success_count == len(config_types),
                "message": f"Loaded {success_count}/{len(config_types)} configuration types",
                "loaded_configs": loaded_configs,
                "consolidated_configs_found": len(required_configs) - len(missing_configs),
            }

        except Exception as e:
            logger.exception(f"Configuration migration validation failed: {e}")
            return {
                "success": False,
                "error": f"Configuration validation failed: {e}",
            }

    async def _compare_functionality(self) -> dict[str, Any]:
        """Compare unified system functionality with legacy scripts."""
        try:
            # Find legacy scripts
            legacy_scripts = self._find_legacy_scripts()

            # Map legacy scripts to unified functionality
            functionality_mapping = {
                "deploy-complete-homelab.sh": "homelab_orchestrator.cli deploy infrastructure",
                "scripts/deploy-homelab.sh": "homelab_orchestrator.cli deploy infrastructure",
                "scripts/health-monitor.sh": "homelab_orchestrator.cli health check",
                "scripts/network-validation.sh": "homelab_orchestrator.cli health check --component networking",
                "check-env-vars.sh": "homelab_orchestrator.cli config validate",
                "run-tests.sh": "homelab_orchestrator.cli status",
            }

            coverage_analysis = {
                "total_legacy_scripts": len(legacy_scripts),
                "mapped_functionality": 0,
                "unmapped_scripts": [],
                "new_functionality": [
                    "Unified configuration management",
                    "Real-time health monitoring",
                    "GPU resource management",
                    "Webhook event processing",
                    "Remote cluster management",
                    "Comprehensive validation framework",
                    "Secure privilege management",
                ],
            }

            # Check which scripts have equivalent functionality
            for script in legacy_scripts:
                script_name = script.name
                if script_name in functionality_mapping:
                    coverage_analysis["mapped_functionality"] += 1
                elif not script_name.startswith(".") and script.suffix in [".sh", ".py"]:
                    # Only count actual scripts, not config files
                    coverage_analysis["unmapped_scripts"].append(script_name)

            coverage_percentage = (
                coverage_analysis["mapped_functionality"]
                / max(coverage_analysis["total_legacy_scripts"], 1)
            ) * 100

            return {
                "success": coverage_percentage >= 80,  # 80% coverage threshold
                "message": f"Functionality coverage: {coverage_percentage:.1f}%",
                "coverage_analysis": coverage_analysis,
                "coverage_percentage": coverage_percentage,
            }

        except Exception as e:
            logger.exception(f"Functionality comparison failed: {e}")
            return {
                "success": False,
                "error": f"Functionality comparison failed: {e}",
            }

    async def _validate_security_posture(self) -> dict[str, Any]:
        """Validate security improvements in unified system."""
        try:
            from homelab_orchestrator.core.config_manager import ConfigManager

            config_manager = ConfigManager.from_environment()

            security_improvements = {
                "privilege_management": False,
                "secure_credential_handling": False,
                "environment_isolation": False,
                "audit_logging": False,
                "configuration_validation": False,
            }

            # Check privilege management
            try:
                from homelab_orchestrator.security import PrivilegeManager

                PrivilegeManager()
                security_improvements["privilege_management"] = True
            except Exception:
                pass

            # Check secure credential handling
            security_config = config_manager.get_security_config()
            if security_config and security_config.get("secrets", {}).get("sealed_secrets", {}).get(
                "enabled",
            ):
                security_improvements["secure_credential_handling"] = True

            # Check environment isolation
            if security_config and security_config.get("default_security_context", {}).get(
                "runAsNonRoot",
            ):
                security_improvements["environment_isolation"] = True

            # Check audit logging
            log_dir = self.project_root / "logs"
            if log_dir.exists():
                security_improvements["audit_logging"] = True

            # Check configuration validation
            validation_result = config_manager.validate_configuration()
            if validation_result["status"] == "valid":
                security_improvements["configuration_validation"] = True

            improvements_count = sum(security_improvements.values())
            total_checks = len(security_improvements)

            return {
                "success": improvements_count >= total_checks * 0.8,  # 80% threshold
                "message": f"Security improvements: {improvements_count}/{total_checks}",
                "security_improvements": security_improvements,
                "improvement_percentage": (improvements_count / total_checks) * 100,
            }

        except Exception as e:
            logger.exception(f"Security validation failed: {e}")
            return {
                "success": False,
                "error": f"Security validation failed: {e}",
            }

    def _find_legacy_scripts(self) -> list[Path]:
        """Find legacy scripts that can be replaced."""
        legacy_patterns = [
            "*.sh",
            "scripts/**/*.sh",
            "scripts/**/*.py",
        ]

        legacy_scripts = []
        for pattern in legacy_patterns:
            legacy_scripts.extend(self.project_root.glob(pattern))

        # Filter out the unified system files
        unified_paths = [
            "homelab_orchestrator",
            "migrate_to_unified_system.py",
        ]

        filtered_scripts = []
        for script in legacy_scripts:
            # Skip if it's part of the unified system
            if any(unified_path in str(script) for unified_path in unified_paths):
                continue
            # Skip if it's in backup or testing directories
            if any(part in script.parts for part in ["backup", "test", "temp", ".git"]):
                continue
            filtered_scripts.append(script)

        return filtered_scripts

    def create_migration_backup(self) -> dict[str, Any]:
        """Create backup of legacy scripts before migration."""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # Find all legacy scripts
            legacy_scripts = self._find_legacy_scripts()

            backed_up = []
            for script in legacy_scripts:
                # Create relative path structure in backup
                rel_path = script.relative_to(self.project_root)
                backup_path = self.backup_dir / rel_path

                # Create parent directories
                backup_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy file
                shutil.copy2(script, backup_path)
                backed_up.append(str(rel_path))

            # Create backup manifest
            manifest = {
                "backup_date": datetime.now().isoformat(),
                "project_root": str(self.project_root),
                "backup_dir": str(self.backup_dir),
                "files_backed_up": len(backed_up),
                "backed_up_files": backed_up,
            }

            manifest_path = self.backup_dir / "backup_manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            return {
                "success": True,
                "backup_dir": str(self.backup_dir),
                "files_backed_up": len(backed_up),
                "manifest_path": str(manifest_path),
            }

        except Exception as e:
            logger.exception(f"Backup creation failed: {e}")
            return {
                "success": False,
                "error": f"Backup creation failed: {e}",
            }

    def display_migration_results(self, results: dict[str, Any]) -> None:
        """Display migration validation results."""
        console.print("\n")
        console.print(Panel("[bold]Migration Validation Results[/bold]"))

        # Overall status
        overall_status = "✅ READY" if results["migration_ready"] else "❌ NOT READY"
        status_color = "green" if results["migration_ready"] else "red"

        console.print(f"\n[{status_color}]Migration Status: {overall_status}[/{status_color}]")

        # Phase results table
        table = Table(title="Validation Phase Results")
        table.add_column("Phase", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details")

        phases = results.get("validation_phases", {})
        for phase_name, phase_result in phases.items():
            status = "✅ PASS" if phase_result.get("success", False) else "❌ FAIL"
            status_color = "green" if phase_result.get("success", False) else "red"

            details = phase_result.get("message", phase_result.get("error", ""))

            table.add_row(
                phase_name.replace("_", " ").title(),
                f"[{status_color}]{status}[/{status_color}]",
                details,
            )

        console.print(table)

        # Recommendations
        if not results["migration_ready"]:
            console.print("\n[yellow]⚠️  Recommendations:[/yellow]")
            console.print("1. Review failed validation phases")
            console.print("2. Fix configuration or system issues")
            console.print("3. Re-run migration validation")
            console.print("4. Only proceed with cleanup after all validations pass")


async def main() -> None:
    """Main migration script."""
    project_root = Path.cwd()

    validator = MigrationValidator(project_root)

    console.print("[bold blue]🚀 Starting Homelab Migration Validation[/bold blue]")

    # Run validation
    results = await validator.run_migration_validation()

    # Display results
    validator.display_migration_results(results)

    # Create backup if migration is ready
    if results["migration_ready"]:
        console.print("\n[green]Creating backup of legacy scripts...[/green]")
        backup_result = validator.create_migration_backup()

        if backup_result["success"]:
            console.print(f"[green]✅ Backup created: {backup_result['backup_dir']}[/green]")
            console.print(f"[green]📁 {backup_result['files_backed_up']} files backed up[/green]")

            console.print("\n[bold green]🎉 Migration validation successful![/bold green]")
            console.print("\n[yellow]Next steps:[/yellow]")
            console.print(
                "1. Review the unified system: `python -m homelab_orchestrator.cli --help`",
            )
            console.print(
                "2. Test deployments: `python -m homelab_orchestrator.cli deploy infrastructure --dry-run`",
            )
            console.print(
                "3. Monitor system health: `python -m homelab_orchestrator.cli health check`",
            )
            console.print("4. Legacy scripts are backed up and can be safely removed")
        else:
            console.print(f"[red]❌ Backup failed: {backup_result.get('error')}[/red]")
    else:
        console.print(
            "\n[red]❌ Migration validation failed - legacy scripts will not be modified[/red]",
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
