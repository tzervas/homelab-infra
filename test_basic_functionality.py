#!/usr/bin/env python3
"""Basic functionality test for unified system."""

import sys
from pathlib import Path


# Add current directory to Python path
sys.path.insert(0, str(Path.cwd()))


def test_imports():
    """Test that core modules can be imported."""
    try:
        from homelab_orchestrator.core.config_manager import ConfigContext, ConfigManager

        print("✅ ConfigManager imported successfully")

        from homelab_orchestrator.core.orchestrator import HomelabOrchestrator

        print("✅ HomelabOrchestrator imported successfully")

        from homelab_orchestrator.security.privilege_manager import (
            PrivilegeContext,
            PrivilegeManager,
        )

        print("✅ PrivilegeManager imported successfully")

        from homelab_orchestrator.validation.validator import SystemValidator

        print("✅ SystemValidator imported successfully")

        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_config_manager():
    """Test basic configuration manager functionality."""
    try:
        from homelab_orchestrator.core.config_manager import ConfigContext, ConfigManager

        # Test with development environment
        context = ConfigContext(
            environment="development",
            cluster_type="local",
        )

        config_manager = ConfigManager(
            project_root=Path.cwd(),
            config_context=context,
        )

        print("✅ ConfigManager initialized successfully")

        # Try to validate configuration
        try:
            validation = config_manager.validate_configuration()
            print(f"✅ Configuration validation: {validation.get('status', 'unknown')}")
        except Exception as e:
            print(f"⚠️  Configuration validation failed: {e}")

        return True
    except Exception as e:
        print(f"❌ ConfigManager test failed: {e}")
        return False


def main():
    """Run basic functionality tests."""
    print("🧪 Testing Basic Unified System Functionality")
    print("=" * 50)

    success = True

    # Test imports
    print("\n1. Testing Module Imports...")
    if not test_imports():
        success = False

    # Test configuration manager
    print("\n2. Testing Configuration Manager...")
    if not test_config_manager():
        success = False

    print("\n" + "=" * 50)
    if success:
        print("✅ Basic functionality tests passed!")
        return 0
    print("❌ Some tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
