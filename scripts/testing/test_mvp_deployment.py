#!/usr/bin/env python3
"""MVP Deployment Test - End-to-end deployment workflow validation.

Tests the complete deployment workflow for MVP readiness:
1. Security validation
2. Configuration validation
3. Orchestrator functionality
4. Basic deployment operations
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

from homelab_orchestrator.__version__ import __version__


# Add the project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import subprocess

from homelab_orchestrator.core.config_manager import ConfigContext, ConfigManager
from homelab_orchestrator.core.orchestrator import HomelabOrchestrator


def setup_logging() -> None:
    """Set up logging for test execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


class MVPDeploymentTest:
    """MVP deployment test suite."""

    def __init__(self) -> None:
        """Initialize test suite."""
        self.logger = logging.getLogger(__name__)
        self.project_root = PROJECT_ROOT
        self.config_context = ConfigContext(
            environment="development",
            cluster_type="local",
        )
        self.config_manager = ConfigManager(
            project_root=self.project_root,
            config_context=self.config_context,
        )
        self.results: dict[str, Any] = {}

    async def test_orchestrator_functionality(self) -> bool:
        """Test basic orchestrator functionality."""
        self.logger.info("🔧 Testing orchestrator functionality")

        try:
            orchestrator = HomelabOrchestrator(
                config_manager=self.config_manager,
                project_root=self.project_root,
                log_level="INFO",
            )

            # Test orchestrator startup
            await orchestrator.start()
            self.logger.info("✅ Orchestrator started successfully")

            # Test configuration validation
            config_result = self.config_manager.validate_configuration()
            if config_result["status"] != "valid":
                self.logger.error(f"❌ Configuration validation failed: {config_result['issues']}")
                return False

            self.logger.info("✅ Configuration validation passed")

            # Test system status
            status = orchestrator.get_system_status()
            if not status:
                self.logger.error("❌ Failed to get system status")
                return False

            self.logger.info("✅ System status check passed")

            # Test dry-run deployment
            result = await orchestrator.deploy_full_infrastructure(
                environment="development",
                components=["metallb"],
                dry_run=True,
            )

            if result.status != "success":
                self.logger.error(f"❌ Dry-run deployment failed: {result.error}")
                return False

            self.logger.info("✅ Dry-run deployment successful")

            # Clean shutdown
            await orchestrator.stop()
            self.logger.info("✅ Orchestrator stopped successfully")

            return True

        except Exception as e:
            self.logger.exception(f"❌ Orchestrator test failed: {e}")
            return False

    def test_security_configuration(self) -> bool:
        """Test security configuration and secrets management."""
        self.logger.info("🔒 Testing security configuration")

        try:
            # Check for hardcoded secrets in OAuth2 configs
            oauth2_file = self.project_root / "kubernetes/base/oauth2-proxy.yaml"
            if oauth2_file.exists():
                content = oauth2_file.read_text()
                if (
                    "aG9tZWxhYi1wb3J0YWwtc2VjcmV0" in content
                    or "SEQzeUMxN1JmR3VYVGg4dXRHWXNLRGZLYUJ2bDhqUXM=" in content
                ):
                    self.logger.error("❌ Found hardcoded secrets in OAuth2 configuration")
                    return False

                if (
                    "${OAUTH2_CLIENT_SECRET}" not in content
                    or "${OAUTH2_COOKIE_SECRET}" not in content
                ):
                    self.logger.error("❌ OAuth2 configuration not using environment variables")
                    return False

            self.logger.info("✅ OAuth2 configuration uses environment variables")

            # Check secret generation script exists
            secret_script = self.project_root / "scripts/security/generate-secrets.sh"
            if not secret_script.exists():
                self.logger.error("❌ Secret generation script not found")
                return False

            if not secret_script.stat().st_mode & 0o111:
                self.logger.error("❌ Secret generation script not executable")
                return False

            self.logger.info("✅ Secret generation script found and executable")

            # Test security configuration loading
            security_config = self.config_manager.get_security_config()
            if not security_config:
                self.logger.error("❌ Failed to load security configuration")
                return False

            self.logger.info("✅ Security configuration loaded successfully")

            return True

        except Exception as e:
            self.logger.exception(f"❌ Security test failed: {e}")
            return False

    def test_version_information(self) -> bool:
        """Test version information and CLI functionality."""
        self.logger.info("📋 Testing version information")

        try:
            # Test CLI version command
            command = [sys.executable, "-m", "homelab_orchestrator", "--version"]
            self.logger.info(f"Running command: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                shell=False,
            )

            if result.returncode != 0:
                self.logger.error("❌ Version command failed")
                return False

            if __version__ not in result.stdout:
                self.logger.error(f"❌ Unexpected version output: {result.stdout}")
                return False

            self.logger.info("✅ Version command works correctly")

            if __version__ not in result.stdout:
                self.logger.error(f"❌ Version mismatch: {__version__}")
                return False

            self.logger.info("✅ Version information correct")

            return True

        except Exception as e:
            self.logger.exception(f"❌ Version test failed: {e}")
            return False

    def test_configuration_validation(self) -> bool:
        """Test comprehensive configuration validation."""
        self.logger.info("⚙️  Testing configuration validation")

        try:
            # Test config validation CLI
            command = [sys.executable, "-m", "homelab_orchestrator", "config", "validate"]
            self.logger.info(f"Running command: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                shell=False,
            )

            if result.returncode != 0:
                self.logger.error(f"❌ Configuration validation failed: {result.stderr}")
                return False

            self.logger.info("✅ Configuration validation CLI works")

            # Test deployment config generation
            deployment_config = self.config_manager.get_deployment_config()

            required_sections = ["networking", "security", "resources", "services"]
            for section in required_sections:
                if section not in deployment_config:
                    self.logger.error(f"❌ Missing required config section: {section}")
                    return False

            self.logger.info("✅ All required configuration sections present")

            return True

        except Exception as e:
            self.logger.exception(f"❌ Configuration validation test failed: {e}")
            return False

    def test_cluster_connectivity(self) -> bool:
        """Test cluster connectivity (if available)."""
        self.logger.info("🔗 Testing cluster connectivity")

        try:
            # Test kubectl availability
            result = subprocess.run(
                ["kubectl", "cluster-info"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                shell=False,
            )

            if result.returncode != 0:
                self.logger.warning("⚠️  No cluster connectivity - this is OK for MVP testing")
                return True  # Not a failure for MVP testing

            self.logger.info("✅ Cluster connectivity verified")
            return True

        except FileNotFoundError:
            self.logger.warning("⚠️  kubectl not found - this is OK for MVP testing")
            return True  # Not a failure for MVP testing
        except Exception as e:
            self.logger.warning(f"⚠️  Cluster connectivity test inconclusive: {e}")
            return True  # Not a failure for MVP testing

    async def run_all_tests(self) -> bool:
        """Run all MVP deployment tests."""
        self.logger.info("🚀 Starting MVP deployment test suite")

        tests = [
            ("Security Configuration", self.test_security_configuration),
            ("Version Information", self.test_version_information),
            ("Configuration Validation", self.test_configuration_validation),
            ("Cluster Connectivity", self.test_cluster_connectivity),
            ("Orchestrator Functionality", self.test_orchestrator_functionality),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            self.logger.info(f"\n--- Running: {test_name} ---")
            try:
                if asyncio.iscoroutinefunction(test_func):
                    success = await test_func()
                else:
                    success = test_func()

                if success:
                    passed += 1
                    self.logger.info(f"✅ {test_name}: PASSED")
                else:
                    self.logger.error(f"❌ {test_name}: FAILED")

            except Exception as e:
                self.logger.exception(f"❌ {test_name}: FAILED with exception: {e}")

        self.logger.info(f"\n🎯 MVP Test Results: {passed}/{total} tests passed")

        if passed == total:
            self.logger.info("🎉 All MVP deployment tests passed! Ready for release.")
            return True
        self.logger.error("❌ Some MVP tests failed. Please address issues before release.")
        return False


async def main() -> None:
    """Main test execution."""
    setup_logging()

    test_suite = MVPDeploymentTest()
    success = await test_suite.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
