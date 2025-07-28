#!/usr/bin/env python3
"""Deployment Smoke Tests for Homelab Infrastructure.

This module provides lightweight smoke tests to verify that key components
are functioning after deployment.
"""

import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List
from urllib.parse import urlparse

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class SmokeTestResult:
    """Result of a smoke test."""
    
    test_name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)


class DeploymentSmokeTests:
    """Lightweight smoke tests for deployment verification."""
    
    def __init__(self, log_level: str = "INFO") -> None:
        """Initialize the smoke test runner."""
        self.logger = self._setup_logging(log_level)
        
        # Core services to test
        self.core_services = {
            "metallb-controller": "metallb-system",
            "cert-manager": "cert-manager",
            "ingress-nginx-controller": "ingress-nginx",
        }
        
        # Optional services (won't fail smoke tests if missing)
        self.optional_services = {
            "longhorn-manager": "longhorn-system",
            "prometheus-operator": "monitoring",
            "grafana": "monitoring",
        }
    
    def _setup_logging(self, level: str) -> logging.Logger:
        """Configure structured logging."""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, level.upper()))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def test_cluster_connectivity(self) -> SmokeTestResult:
        """Test basic cluster connectivity."""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ["kubectl", "cluster-info"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                return SmokeTestResult(
                    test_name="cluster_connectivity",
                    passed=True,
                    message="Kubernetes cluster is accessible",
                    duration=duration,
                    details={"cluster_info": result.stdout.strip()},
                )
            else:
                return SmokeTestResult(
                    test_name="cluster_connectivity",
                    passed=False,
                    message="Cannot connect to Kubernetes cluster",
                    duration=duration,
                    details={"error": result.stderr.strip()},
                )
                
        except Exception as e:
            duration = time.time() - start_time
            return SmokeTestResult(
                test_name="cluster_connectivity",
                passed=False,
                message=f"Cluster connectivity test failed: {e}",
                duration=duration,
            )
    
    def test_core_namespaces(self) -> SmokeTestResult:
        """Test that core namespaces exist."""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ["kubectl", "get", "namespaces", "-o", "json"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            
            duration = time.time() - start_time
            
            if result.returncode != 0:
                return SmokeTestResult(
                    test_name="core_namespaces",
                    passed=False,
                    message="Failed to retrieve namespaces",
                    duration=duration,
                    details={"error": result.stderr.strip()},
                )
            
            namespaces_data = json.loads(result.stdout)
            existing_namespaces = [
                ns["metadata"]["name"] 
                for ns in namespaces_data.get("items", [])
            ]
            
            # Check for required namespaces
            required_namespaces = [
                "kube-system", "metallb-system", "cert-manager", "ingress-nginx"
            ]
            
            missing_namespaces = [
                ns for ns in required_namespaces 
                if ns not in existing_namespaces
            ]
            
            if missing_namespaces:
                return SmokeTestResult(
                    test_name="core_namespaces",
                    passed=False,
                    message=f"Missing required namespaces: {', '.join(missing_namespaces)}",
                    duration=duration,
                    details={
                        "existing_namespaces": existing_namespaces,
                        "missing_namespaces": missing_namespaces,
                    },
                )
            else:
                return SmokeTestResult(
                    test_name="core_namespaces",
                    passed=True,
                    message="All core namespaces exist",
                    duration=duration,
                    details={"existing_namespaces": existing_namespaces},
                )
                
        except Exception as e:
            duration = time.time() - start_time
            return SmokeTestResult(
                test_name="core_namespaces",
                passed=False,
                message=f"Namespace test failed: {e}",
                duration=duration,
            )
    
    def test_core_deployments(self) -> SmokeTestResult:
        """Test that core deployments are ready."""
        start_time = time.time()
        
        try:
            deployment_results = {}
            failed_deployments = []
            
            for deployment, namespace in self.core_services.items():
                result = subprocess.run(
                    ["kubectl", "get", "deployment", deployment, "-n", namespace, "-o", "json"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
                
                if result.returncode == 0:
                    deployment_data = json.loads(result.stdout)
                    status = deployment_data.get("status", {})
                    ready_replicas = status.get("readyReplicas", 0)
                    desired_replicas = status.get("replicas", 0)
                    
                    is_ready = ready_replicas == desired_replicas and desired_replicas > 0
                    deployment_results[f"{namespace}/{deployment}"] = {
                        "ready": is_ready,
                        "ready_replicas": ready_replicas,
                        "desired_replicas": desired_replicas,
                    }
                    
                    if not is_ready:
                        failed_deployments.append(f"{namespace}/{deployment}")
                else:
                    deployment_results[f"{namespace}/{deployment}"] = {
                        "ready": False,
                        "error": result.stderr.strip(),
                    }
                    failed_deployments.append(f"{namespace}/{deployment}")
            
            duration = time.time() - start_time
            
            if failed_deployments:
                return SmokeTestResult(
                    test_name="core_deployments",
                    passed=False,
                    message=f"Core deployments not ready: {', '.join(failed_deployments)}",
                    duration=duration,
                    details={"deployment_results": deployment_results},
                )
            else:
                return SmokeTestResult(
                    test_name="core_deployments",
                    passed=True,
                    message="All core deployments are ready",
                    duration=duration,
                    details={"deployment_results": deployment_results},
                )
                
        except Exception as e:
            duration = time.time() - start_time
            return SmokeTestResult(
                test_name="core_deployments",
                passed=False,
                message=f"Deployment test failed: {e}",
                duration=duration,
            )
    
    def test_ingress_controller(self) -> SmokeTestResult:
        """Test that ingress controller is responding."""
        start_time = time.time()
        
        try:
            # Check if ingress controller service exists and has endpoints
            result = subprocess.run(
                ["kubectl", "get", "service", "ingress-nginx-controller", "-n", "ingress-nginx", "-o", "json"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            
            duration = time.time() - start_time
            
            if result.returncode != 0:
                return SmokeTestResult(
                    test_name="ingress_controller",
                    passed=False,
                    message="Ingress controller service not found",
                    duration=duration,
                    details={"error": result.stderr.strip()},
                )
            
            service_data = json.loads(result.stdout)
            service_type = service_data.get("spec", {}).get("type", "")
            
            if service_type == "LoadBalancer":
                # Check if LoadBalancer has external IP
                load_balancer = service_data.get("status", {}).get("loadBalancer", {})
                ingress_ips = load_balancer.get("ingress", [])
                
                if ingress_ips:
                    external_ip = ingress_ips[0].get("ip", "")
                    return SmokeTestResult(
                        test_name="ingress_controller",
                        passed=True,
                        message=f"Ingress controller accessible at {external_ip}",
                        duration=duration,
                        details={
                            "service_type": service_type,
                            "external_ip": external_ip,
                        },
                    )
                else:
                    return SmokeTestResult(
                        test_name="ingress_controller",
                        passed=False,
                        message="LoadBalancer service has no external IP assigned",
                        duration=duration,
                        details={"service_type": service_type},
                    )
            else:
                return SmokeTestResult(
                    test_name="ingress_controller",
                    passed=True,
                    message=f"Ingress controller service exists (type: {service_type})",
                    duration=duration,
                    details={"service_type": service_type},
                )
                
        except Exception as e:
            duration = time.time() - start_time
            return SmokeTestResult(
                test_name="ingress_controller",
                passed=False,
                message=f"Ingress controller test failed: {e}",
                duration=duration,
            )
    
    def test_certificate_management(self) -> SmokeTestResult:
        """Test that cert-manager is working."""
        start_time = time.time()
        
        try:
            # Check if cert-manager CRDs exist
            result = subprocess.run(
                ["kubectl", "get", "crd", "certificates.cert-manager.io"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            
            duration = time.time() - start_time
            
            if result.returncode != 0:
                return SmokeTestResult(
                    test_name="certificate_management",
                    passed=False,
                    message="cert-manager CRDs not installed",
                    duration=duration,
                    details={"error": result.stderr.strip()},
                )
            
            # Check if cert-manager webhook is responding
            webhook_result = subprocess.run(
                ["kubectl", "get", "deployment", "cert-manager-webhook", "-n", "cert-manager"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            
            if webhook_result.returncode == 0:
                return SmokeTestResult(
                    test_name="certificate_management",
                    passed=True,
                    message="cert-manager is installed and webhook is available",
                    duration=duration,
                )
            else:
                return SmokeTestResult(
                    test_name="certificate_management",
                    passed=False,
                    message="cert-manager webhook deployment not found",
                    duration=duration,
                    details={"webhook_error": webhook_result.stderr.strip()},
                )
                
        except Exception as e:
            duration = time.time() - start_time
            return SmokeTestResult(
                test_name="certificate_management",
                passed=False,
                message=f"Certificate management test failed: {e}",
                duration=duration,
            )
    
    def test_dns_resolution(self) -> SmokeTestResult:
        """Test DNS resolution within the cluster."""
        start_time = time.time()
        
        try:
            # Test DNS resolution using a temporary pod
            result = subprocess.run([
                "kubectl", "run", "dns-test", 
                "--image=busybox", "--rm", "-i", "--restart=Never", "--",
                "nslookup", "kubernetes.default"
            ], capture_output=True, text=True, timeout=60, check=False)
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                return SmokeTestResult(
                    test_name="dns_resolution",
                    passed=True,
                    message="DNS resolution is working",
                    duration=duration,
                    details={"nslookup_output": result.stdout.strip()},
                )
            else:
                return SmokeTestResult(
                    test_name="dns_resolution",
                    passed=False,
                    message="DNS resolution failed",
                    duration=duration,
                    details={"error": result.stderr.strip()},
                )
                
        except Exception as e:
            duration = time.time() - start_time
            return SmokeTestResult(
                test_name="dns_resolution",
                passed=False,
                message=f"DNS resolution test failed: {e}",
                duration=duration,
            )
    
    def run_all_smoke_tests(self) -> List[SmokeTestResult]:
        """Run all smoke tests."""
        self.logger.info("Running deployment smoke tests...")
        
        tests = [
            self.test_cluster_connectivity,
            self.test_core_namespaces,
            self.test_core_deployments,
            self.test_ingress_controller,
            self.test_certificate_management,
            self.test_dns_resolution,
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
                
                status = "✅ PASS" if result.passed else "❌ FAIL"
                self.logger.info(f"{status} {result.test_name}: {result.message}")
                
            except Exception as e:
                self.logger.exception(f"Test {test.__name__} failed with exception: {e}")
                results.append(SmokeTestResult(
                    test_name=test.__name__,
                    passed=False,
                    message=f"Test failed with exception: {e}",
                ))
        
        return results


def main() -> int:
    """Main function for standalone testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run deployment smoke tests")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument(
        "--test",
        choices=["connectivity", "namespaces", "deployments", "ingress", "certificates", "dns"],
        help="Run specific test only",
    )
    
    args = parser.parse_args()
    
    smoke_tests = DeploymentSmokeTests(log_level=args.log_level)
    
    if args.test:
        # Run specific test
        test_map = {
            "connectivity": smoke_tests.test_cluster_connectivity,
            "namespaces": smoke_tests.test_core_namespaces,
            "deployments": smoke_tests.test_core_deployments,
            "ingress": smoke_tests.test_ingress_controller,
            "certificates": smoke_tests.test_certificate_management,
            "dns": smoke_tests.test_dns_resolution,
        }
        
        result = test_map[args.test]()
        
        print(f"\n🧪 {result.test_name.title()} Smoke Test:")
        print(f"Status: {'✅ PASS' if result.passed else '❌ FAIL'}")
        print(f"Message: {result.message}")
        print(f"Duration: {result.duration:.2f}s")
        
        if result.details:
            print(f"Details: {result.details}")
        
        return 0 if result.passed else 1
    
    # Run all smoke tests
    results = smoke_tests.run_all_smoke_tests()
    
    print("\n🧪 Deployment Smoke Test Results:")
    print("="*50)
    
    passed_tests = sum(1 for r in results if r.passed)
    total_tests = len(results)
    total_duration = sum(r.duration for r in results)
    
    for result in results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"  {status} {result.test_name}: {result.message}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    print(f"Total duration: {total_duration:.2f}s")
    
    return 0 if passed_tests == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())
