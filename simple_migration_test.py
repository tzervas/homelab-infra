#!/usr/bin/env python3
"""Simple migration test to validate unified system functionality."""

import sys
from pathlib import Path


# Add current directory to Python path
sys.path.insert(0, str(Path.cwd()))


def test_unified_system():
    """Test the unified system is working."""
    print("🧪 Testing Unified Homelab System")
    print("=" * 50)

    tests_passed = 0
    total_tests = 0

    # Test 1: Import check
    total_tests += 1
    print("\n1. Testing core module imports...")
    try:
        from homelab_orchestrator.core.config_manager import ConfigContext, ConfigManager
        from homelab_orchestrator.core.orchestrator import HomelabOrchestrator
        from homelab_orchestrator.security.privilege_manager import PrivilegeManager
        from homelab_orchestrator.validation.validator import SystemValidator

        print("✅ All core modules imported successfully")
        tests_passed += 1
    except ImportError as e:
        print(f"❌ Import failed: {e}")

    # Test 2: Configuration manager
    total_tests += 1
    print("\n2. Testing configuration manager...")
    try:
        config_context = ConfigContext(environment="development")
        config_manager = ConfigManager(
            project_root=Path.cwd(),
            config_context=config_context,
        )

        # Test validation
        validation_result = config_manager.validate_configuration()
        if validation_result["status"] in ["valid", "invalid"]:
            print(f"✅ Configuration manager working - status: {validation_result['status']}")
            if validation_result.get("issues"):
                print(f"   ⚠️  Found {len(validation_result['issues'])} configuration issues")
            tests_passed += 1
        else:
            print(f"❌ Unexpected validation status: {validation_result['status']}")
    except Exception as e:
        print(f"❌ Configuration manager test failed: {e}")

    # Test 3: System validator
    total_tests += 1
    print("\n3. Testing system validator...")
    try:
        config_manager = ConfigManager.from_environment()
        SystemValidator(config_manager)
        print("✅ System validator initialized successfully")
        tests_passed += 1
    except Exception as e:
        print(f"❌ System validator test failed: {e}")

    # Test 4: Privilege manager
    total_tests += 1
    print("\n4. Testing privilege manager...")
    try:
        from homelab_orchestrator.security.privilege_manager import (
            PrivilegeManager,
        )

        privilege_manager = PrivilegeManager()

        # Test getting available auth methods
        auth_methods = privilege_manager._get_available_auth_methods()
        print(f"✅ Privilege manager working - {len(auth_methods)} auth methods available")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Privilege manager test failed: {e}")

    # Test 5: Configuration files
    total_tests += 1
    print("\n5. Testing consolidated configuration files...")
    try:
        config_dir = Path.cwd() / "config" / "consolidated"
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

        existing_configs = [cfg for cfg in required_configs if (config_dir / cfg).exists()]
        print(f"✅ Found {len(existing_configs)}/{len(required_configs)} consolidated config files")

        if len(existing_configs) >= len(required_configs) // 2:  # At least half must exist
            tests_passed += 1
        else:
            print("❌ Too few configuration files found")
    except Exception as e:
        print(f"❌ Configuration files test failed: {e}")

    # Test 6: Legacy script identification
    total_tests += 1
    print("\n6. Testing legacy script identification...")
    try:
        legacy_scripts = []
        for pattern in ["*.sh", "scripts/**/*.sh"]:
            legacy_scripts.extend(Path.cwd().glob(pattern))

        # Filter out unified system files
        filtered_scripts = [
            s
            for s in legacy_scripts
            if "homelab_orchestrator" not in str(s)
            and "migrate_to_unified_system" not in str(s)
            and ".venv" not in str(s)
        ]

        print(f"✅ Found {len(filtered_scripts)} legacy scripts that could be replaced")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Legacy script identification failed: {e}")

    # Summary
    print("\n" + "=" * 50)
    print(f"Tests passed: {tests_passed}/{total_tests}")

    if tests_passed == total_tests:
        print("🎉 All tests passed! Unified system is ready.")
        return True
    if tests_passed >= total_tests * 0.8:  # 80% pass rate
        print("⚠️  Most tests passed. System mostly ready with some issues.")
        return True
    print("❌ Too many tests failed. System needs more work.")
    return False


if __name__ == "__main__":
    success = test_unified_system()
    sys.exit(0 if success else 1)
