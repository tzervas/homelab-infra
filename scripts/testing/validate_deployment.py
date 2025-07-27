#!/usr/bin/env python3
"""
Automated Deployment Validation Script

This script runs all validation tests in the correct order and provides
a comprehensive deployment readiness assessment.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Import all testing modules
try:
    from .test_reporter import HomelabTestReporter
    from .rootless_compatibility import RootlessCompatibilityChecker
    from .permission_verifier import PermissionVerifier
    from .issue_tracker import IssueTracker, IssueSeverity
except ImportError:
    try:
        from test_reporter import HomelabTestReporter
        from rootless_compatibility import RootlessCompatibilityChecker
        from permission_verifier import PermissionVerifier
        from issue_tracker import IssueTracker, IssueSeverity
    except ImportError as e:
        print(f"Error importing testing modules: {e}")
        sys.exit(1)


class DeploymentValidator:
    """Comprehensive deployment validation orchestrator."""
    
    def __init__(self, kubeconfig_path: str = None, deployment_user: str = None, log_level: str = "INFO"):
        """Initialize the deployment validator."""
        self.kubeconfig_path = kubeconfig_path
        self.deployment_user = deployment_user or os.getenv("HOMELAB_USER", "homelab-deploy")
        self.log_level = log_level
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.issue_tracker = IssueTracker()
        self.results = {}
        
    def run_compatibility_check(self) -> Dict[str, Any]:
        """Run rootless compatibility validation with architecture detection."""
        self.logger.info("🔍 Running architecture-aware rootless compatibility check...")
        
        try:
            checker = RootlessCompatibilityChecker(
                kubeconfig_path=self.kubeconfig_path,
                log_level=self.log_level
            )
            
            # Log detected architecture
            self.logger.info(f"Detected deployment architecture: {checker.deployment_mode}")
            
            results = checker.run_comprehensive_compatibility_check()
            compatible_count = sum(1 for r in results if r.compatible)
            total_count = len(results)
            
            return {
                "status": "pass" if compatible_count == total_count else "fail",
                "compatible_components": compatible_count,
                "total_components": total_count,
                "deployment_mode": checker.deployment_mode,
                "bastion_host": checker.bastion_host,
                "results": [
                    {
                        "component": r.component,
                        "compatible": r.compatible,
                        "issues": r.issues,
                        "recommendations": r.recommendations,
                        "details": r.details
                    }
                    for r in results
                ]
            }
        except Exception as e:
            self.logger.error(f"Compatibility check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "compatible_components": 0,
                "total_components": 0
            }
    
    def run_permission_verification(self) -> Dict[str, Any]:
        """Run permission verification tests."""
        self.logger.info("🔐 Running permission verification...")
        
        try:
            verifier = PermissionVerifier(
                deployment_user=self.deployment_user,
                kubeconfig_path=self.kubeconfig_path,
                log_level=self.log_level
            )
            
            results = verifier.run_comprehensive_permission_tests()
            
            total_tests = sum(len(test_results) for test_results in results.values())
            passed_tests = sum(sum(1 for result in test_results if result.passed) for test_results in results.values())
            
            return {
                "status": "pass" if passed_tests == total_tests else "fail",
                "passed_tests": passed_tests,
                "total_tests": total_tests,
                "categories": {
                    category: {
                        "passed": sum(1 for result in test_results if result.passed),
                        "total": len(test_results),
                        "failed_tests": [
                            {
                                "name": result.test.name,
                                "description": result.test.description,
                                "error": result.error
                            }
                            for result in test_results if not result.passed
                        ]
                    }
                    for category, test_results in results.items()
                }
            }
        except Exception as e:
            self.logger.error(f"Permission verification failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "passed_tests": 0,
                "total_tests": 0
            }
    
    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive infrastructure tests."""
        self.logger.info("🧪 Running comprehensive infrastructure tests...")
        
        try:
            reporter = HomelabTestReporter(
                kubeconfig_path=self.kubeconfig_path,
                log_level=self.log_level
            )
            
            result = reporter.run_comprehensive_test_suite()
            
            return {
                "status": result.overall_status,
                "duration": result.duration,
                "modules_tested": result.summary.get("modules_run", 0),
                "recommendations": len(result.recommendations or []),
                "timestamp": result.timestamp
            }
        except Exception as e:
            self.logger.error(f"Comprehensive tests failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "duration": 0,
                "modules_tested": 0
            }
    
    def run_all_validations(self) -> Dict[str, Any]:
        """Run all validation tests in sequence."""
        start_time = time.time()
        
        self.logger.info("🚀 Starting comprehensive deployment validation...")
        
        # Clear any previous issues
        self.issue_tracker.clear()
        
        # Run all validation phases
        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "deployment_user": self.deployment_user,
            "compatibility_check": self.run_compatibility_check(),
            "permission_verification": self.run_permission_verification(),
            "infrastructure_tests": self.run_comprehensive_tests()
        }
        
        # Calculate overall status
        statuses = [
            validation_results["compatibility_check"]["status"],
            validation_results["permission_verification"]["status"],
            validation_results["infrastructure_tests"]["status"]
        ]
        
        if "error" in statuses:
            overall_status = "error"
        elif "fail" in statuses:
            overall_status = "fail"
        else:
            overall_status = "pass"
        
        validation_results["overall_status"] = overall_status
        validation_results["duration"] = time.time() - start_time
        
        # Generate summary
        validation_results["summary"] = self._generate_summary(validation_results)
        
        self.logger.info(f"✅ Validation completed in {validation_results['duration']:.2f}s with status: {overall_status.upper()}")
        
        return validation_results
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate validation summary."""
        compatibility = results["compatibility_check"]
        permissions = results["permission_verification"]
        infrastructure = results["infrastructure_tests"]
        
        summary = {
            "overall_status": results["overall_status"],
            "deployment_ready": results["overall_status"] == "pass",
            "issues_found": [],
            "recommendations": [],
            "next_steps": []
        }
        
        # Compatibility issues
        if compatibility["status"] != "pass":
            compatible = compatibility.get("compatible_components", 0)
            total = compatibility.get("total_components", 0)
            summary["issues_found"].append(f"Compatibility: {compatible}/{total} components ready")
            
            if "results" in compatibility:
                for result in compatibility["results"]:
                    if not result["compatible"]:
                        summary["issues_found"].extend(result["issues"][:3])  # Top 3 issues
                        summary["recommendations"].extend(result["recommendations"][:2])  # Top 2 recommendations
        
        # Permission issues
        if permissions["status"] != "pass":
            passed = permissions.get("passed_tests", 0)
            total = permissions.get("total_tests", 0)
            summary["issues_found"].append(f"Permissions: {passed}/{total} tests passed")
            
            if "categories" in permissions:
                for category, data in permissions["categories"].items():
                    for failed_test in data.get("failed_tests", [])[:2]:  # Top 2 per category
                        summary["issues_found"].append(f"{category}: {failed_test['description']}")
        
        # Infrastructure issues
        if infrastructure["status"] not in ["pass", "warning"]:
            summary["issues_found"].append(f"Infrastructure: {infrastructure['status']}")
        
        # Generate next steps
        if results["overall_status"] != "pass":
            if compatibility["status"] != "pass":
                summary["next_steps"].append("1. Fix compatibility issues (run setup-secure-deployment.sh if needed)")
            
            if permissions["status"] != "pass":
                summary["next_steps"].append("2. Resolve permission issues (check sudo configuration)")
            
            if infrastructure["status"] != "pass":
                summary["next_steps"].append("3. Address infrastructure issues (check service deployments)")
            
            summary["next_steps"].append("4. Re-run validation after fixes")
        else:
            summary["next_steps"].append("✅ All validations passed - deployment is ready!")
        
        return summary
    
    def print_console_summary(self, results: Dict[str, Any]) -> None:
        """Print validation summary to console."""
        print(f"\n🏠 HOMELAB DEPLOYMENT VALIDATION REPORT")
        print(f"{'='*60}")
        print(f"Timestamp: {results['timestamp']}")
        print(f"Duration: {results['duration']:.2f}s")
        print(f"Overall Status: {results['overall_status'].upper()}")
        print(f"Deployment Ready: {'✅ YES' if results['summary']['deployment_ready'] else '❌ NO'}")
        
        # Display architecture information if available
        compatibility = results.get("compatibility_check", {})
        if "deployment_mode" in compatibility:
            print(f"")
            print(f"🏗️  DEPLOYMENT ARCHITECTURE:")
            print(f"  Mode: {compatibility['deployment_mode']}")
            print(f"  Bastion: {compatibility.get('bastion_host', 'N/A')}")
        
        print(f"{'='*60}")
        
        # Component status
        compatibility = results["compatibility_check"]
        permissions = results["permission_verification"]
        infrastructure = results["infrastructure_tests"]
        
        print(f"\n📊 COMPONENT STATUS:")
        
        # Compatibility
        if compatibility["status"] != "error":
            compatible = compatibility.get("compatible_components", 0)
            total = compatibility.get("total_components", 0)
            status_icon = "✅" if compatible == total else "❌"
            print(f"  {status_icon} Compatibility: {compatible}/{total} components ready")
        else:
            print(f"  ❌ Compatibility: Error - {compatibility.get('error', 'Unknown error')}")
        
        # Permissions
        if permissions["status"] != "error":
            passed = permissions.get("passed_tests", 0)
            total = permissions.get("total_tests", 0)
            status_icon = "✅" if passed == total else "❌"
            print(f"  {status_icon} Permissions: {passed}/{total} tests passed")
        else:
            print(f"  ❌ Permissions: Error - {permissions.get('error', 'Unknown error')}")
        
        # Infrastructure
        status_icon = "✅" if infrastructure["status"] == "pass" else "⚠️" if infrastructure["status"] == "warning" else "❌"
        print(f"  {status_icon} Infrastructure: {infrastructure['status']}")
        
        # Issues and recommendations
        summary = results["summary"]
        
        if summary["issues_found"]:
            print(f"\n🚨 ISSUES FOUND ({len(summary['issues_found'])}):")
            for i, issue in enumerate(summary["issues_found"][:10], 1):  # Show top 10
                print(f"  {i}. {issue}")
            
            if len(summary["issues_found"]) > 10:
                print(f"  ... and {len(summary['issues_found']) - 10} more issues")
        
        if summary["recommendations"]:
            print(f"\n💡 RECOMMENDATIONS ({len(summary['recommendations'])}):")
            for i, rec in enumerate(summary["recommendations"][:5], 1):  # Show top 5
                print(f"  {i}. {rec}")
        
        if summary["next_steps"]:
            print(f"\n🔧 NEXT STEPS:")
            for step in summary["next_steps"]:
                print(f"  {step}")
        
        print(f"\n{'='*60}")
    
    def export_results(self, results: Dict[str, Any], output_file: str = None) -> str:
        """Export validation results to file."""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"deployment_validation_{timestamp}.json"
        
        # Ensure results directory exists
        results_dir = Path("test_results")
        results_dir.mkdir(exist_ok=True)
        
        output_path = results_dir / output_file
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        self.logger.info(f"Validation results exported to: {output_path}")
        return str(output_path)


def main():
    """Main function for deployment validation."""
    parser = argparse.ArgumentParser(description="Comprehensive deployment validation")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument("--deployment-user", help="Deployment user to validate", default="homelab-deploy")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARN", "ERROR"])
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--quiet", action="store_true", help="Suppress console output")
    parser.add_argument("--export-only", action="store_true", help="Only export results, don't print to console")
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = DeploymentValidator(
        kubeconfig_path=args.kubeconfig,
        deployment_user=args.deployment_user,
        log_level=args.log_level
    )
    
    # Run all validations
    results = validator.run_all_validations()
    
    # Export results if requested
    if args.output or args.export_only:
        output_file = validator.export_results(results, args.output)
        if args.export_only:
            print(f"Results exported to: {output_file}")
            return 0
    
    # Print console summary unless quiet
    if not args.quiet:
        validator.print_console_summary(results)
    
    # Exit with appropriate code
    if results["overall_status"] == "pass":
        return 0
    elif results["overall_status"] == "warning":
        return 1
    else:
        return 2


if __name__ == "__main__":
    sys.exit(main())