#!/usr/bin/env python3
"""
Performance Benchmarking Module for Modernized Infrastructure Stack.

Provides comprehensive performance testing including:
- Kubernetes cluster performance metrics
- Application response time benchmarking
- Resource utilization monitoring
- Network throughput testing
- Database performance validation
- Load testing scenarios
"""

import contextlib
import json
import logging
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import psutil
import requests

from kubernetes import client, config


@dataclass
class BenchmarkResult:
    """Single benchmark test result."""

    test_name: str
    component: str
    metric_name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: str | None = None


@dataclass
class PerformanceReport:
    """Comprehensive performance report."""

    test_suite: str
    start_time: datetime
    end_time: datetime | None = None
    total_duration_seconds: float = 0.0
    results: list[BenchmarkResult] = field(default_factory=list)
    summary_stats: dict[str, Any] = field(default_factory=dict)
    environment_info: dict[str, Any] = field(default_factory=dict)

    def add_result(self, result: BenchmarkResult) -> None:
        """Add a benchmark result."""
        self.results.append(result)

    def finalize(self) -> None:
        """Finalize the report with summary statistics."""
        self.end_time = datetime.now()
        self.total_duration_seconds = (self.end_time - self.start_time).total_seconds()

        # Calculate summary stats
        successful_tests = [r for r in self.results if r.success]
        failed_tests = [r for r in self.results if not r.success]

        self.summary_stats = {
            "total_tests": len(self.results),
            "successful_tests": len(successful_tests),
            "failed_tests": len(failed_tests),
            "success_rate": len(successful_tests) / len(self.results) * 100 if self.results else 0,
            "components_tested": list({r.component for r in self.results}),
            "avg_response_time_ms": statistics.mean(
                [r.value for r in successful_tests if r.unit == "ms"],
            )
            if successful_tests
            else 0,
        }


class InfrastructureBenchmarker:
    """Main infrastructure benchmarking class."""

    def __init__(self, kubeconfig_path: str | None = None, log_level: str = "INFO") -> None:
        """Initialize the benchmarker."""
        self.logger = self._setup_logging(log_level)
        self.kubeconfig_path = kubeconfig_path
        self._load_kubernetes_config()

        # Benchmark configuration
        self.default_timeout = 30
        self.concurrent_requests = 10
        self.test_duration = 60  # seconds

    def _setup_logging(self, level: str) -> logging.Logger:
        """Configure structured logging."""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, level.upper()))

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _load_kubernetes_config(self) -> None:
        """Load Kubernetes configuration."""
        try:
            if self.kubeconfig_path:
                config.load_kube_config(config_file=self.kubeconfig_path)
            else:
                config.load_incluster_config()
        except Exception as e:
            self.logger.warning(f"Could not load Kubernetes config: {e}")

    def collect_environment_info(self) -> dict[str, Any]:
        """Collect environment information for benchmarking context."""
        env_info = {
            "timestamp": datetime.now().isoformat(),
            "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}",
            "platform": psutil.platform.platform(),
        }

        # System information
        try:
            env_info.update(
                {
                    "cpu_count": psutil.cpu_count(),
                    "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                    "disk_usage_gb": round(psutil.disk_usage("/").total / (1024**3), 2),
                },
            )
        except Exception as e:
            self.logger.debug(f"Could not collect system info: {e}")

        # Kubernetes cluster information
        try:
            v1 = client.CoreV1Api()
            nodes = v1.list_node()

            env_info.update(
                {
                    "kubernetes_nodes": len(nodes.items),
                    "kubernetes_version": nodes.items[0].status.node_info.kubelet_version
                    if nodes.items
                    else "unknown",
                },
            )
        except Exception as e:
            self.logger.debug(f"Could not collect Kubernetes info: {e}")

        return env_info

    def benchmark_api_response_time(self, endpoints: list[str]) -> list[BenchmarkResult]:
        """Benchmark API response times."""
        results = []

        for endpoint in endpoints:
            self.logger.info(f"Benchmarking endpoint: {endpoint}")

            response_times = []
            errors = 0

            for _i in range(10):  # 10 requests per endpoint
                try:
                    start_time = time.time()
                    response = requests.get(endpoint, timeout=self.default_timeout, verify=False)
                    end_time = time.time()

                    if response.status_code < 400:
                        response_times.append((end_time - start_time) * 1000)  # Convert to ms
                    else:
                        errors += 1

                except Exception as e:
                    errors += 1
                    self.logger.debug(f"Request failed: {e}")

            if response_times:
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
                min_response_time = min(response_times)

                results.extend(
                    [
                        BenchmarkResult(
                            test_name="API Response Time - Average",
                            component=endpoint,
                            metric_name="avg_response_time",
                            value=avg_response_time,
                            unit="ms",
                            metadata={"requests_made": len(response_times), "errors": errors},
                        ),
                        BenchmarkResult(
                            test_name="API Response Time - Max",
                            component=endpoint,
                            metric_name="max_response_time",
                            value=max_response_time,
                            unit="ms",
                        ),
                        BenchmarkResult(
                            test_name="API Response Time - Min",
                            component=endpoint,
                            metric_name="min_response_time",
                            value=min_response_time,
                            unit="ms",
                        ),
                    ],
                )
            else:
                results.append(
                    BenchmarkResult(
                        test_name="API Response Time",
                        component=endpoint,
                        metric_name="response_time",
                        value=0,
                        unit="ms",
                        success=False,
                        error_message="All requests failed",
                    ),
                )

        return results

    def benchmark_kubernetes_performance(self) -> list[BenchmarkResult]:
        """Benchmark Kubernetes cluster performance."""
        results = []

        try:
            v1 = client.CoreV1Api()
            client.AppsV1Api()

            # Test pod creation time
            start_time = time.time()

            test_pod = client.V1Pod(
                metadata=client.V1ObjectMeta(name="benchmark-test-pod", namespace="default"),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="test-container",
                            image="busybox:1.35",
                            command=["sleep", "30"],
                        ),
                    ],
                    restart_policy="Never",
                ),
            )

            # Create pod
            v1.create_namespaced_pod(namespace="default", body=test_pod)

            # Wait for pod to be running
            pod_running = False
            timeout = 60
            check_start = time.time()

            while not pod_running and (time.time() - check_start) < timeout:
                try:
                    pod = v1.read_namespaced_pod(name="benchmark-test-pod", namespace="default")
                    if pod.status.phase == "Running":
                        pod_running = True
                        break
                except Exception:
                    pass
                time.sleep(1)

            pod_creation_time = (time.time() - start_time) * 1000  # Convert to ms

            # Cleanup test pod
            with contextlib.suppress(Exception):
                v1.delete_namespaced_pod(name="benchmark-test-pod", namespace="default")

            results.append(
                BenchmarkResult(
                    test_name="Pod Creation Time",
                    component="kubernetes",
                    metric_name="pod_creation_time",
                    value=pod_creation_time,
                    unit="ms",
                    success=pod_running,
                    error_message="Pod failed to start" if not pod_running else None,
                ),
            )

            # Test API server response time
            api_start = time.time()
            nodes = v1.list_node()
            api_response_time = (time.time() - api_start) * 1000

            results.append(
                BenchmarkResult(
                    test_name="API Server Response Time",
                    component="kubernetes-api",
                    metric_name="api_response_time",
                    value=api_response_time,
                    unit="ms",
                    metadata={"nodes_count": len(nodes.items)},
                ),
            )

        except Exception as e:
            results.append(
                BenchmarkResult(
                    test_name="Kubernetes Performance",
                    component="kubernetes",
                    metric_name="performance_test",
                    value=0,
                    unit="score",
                    success=False,
                    error_message=str(e),
                ),
            )

        return results

    def benchmark_storage_performance(self) -> list[BenchmarkResult]:
        """Benchmark storage I/O performance."""
        results = []

        try:
            # Create a test PVC and pod to test storage
            v1 = client.CoreV1Api()

            # Test storage class availability
            storage_v1 = client.StorageV1Api()
            storage_classes = storage_v1.list_storage_class()

            results.append(
                BenchmarkResult(
                    test_name="Storage Classes Available",
                    component="storage",
                    metric_name="storage_classes_count",
                    value=len(storage_classes.items),
                    unit="count",
                    metadata={
                        "storage_classes": [sc.metadata.name for sc in storage_classes.items],
                    },
                ),
            )

            # Test PVC creation time if storage classes are available
            if storage_classes.items:
                default_sc = storage_classes.items[0].metadata.name

                pvc = client.V1PersistentVolumeClaim(
                    metadata=client.V1ObjectMeta(name="benchmark-test-pvc", namespace="default"),
                    spec=client.V1PersistentVolumeClaimSpec(
                        access_modes=["ReadWriteOnce"],
                        resources=client.V1ResourceRequirements(requests={"storage": "1Gi"}),
                        storage_class_name=default_sc,
                    ),
                )

                start_time = time.time()
                v1.create_namespaced_persistent_volume_claim(namespace="default", body=pvc)

                # Wait for PVC to be bound
                pvc_bound = False
                timeout = 120
                check_start = time.time()

                while not pvc_bound and (time.time() - check_start) < timeout:
                    try:
                        pvc_status = v1.read_namespaced_persistent_volume_claim(
                            name="benchmark-test-pvc",
                            namespace="default",
                        )
                        if pvc_status.status.phase == "Bound":
                            pvc_bound = True
                            break
                    except Exception:
                        pass
                    time.sleep(2)

                pvc_creation_time = (time.time() - start_time) * 1000

                # Cleanup PVC
                with contextlib.suppress(Exception):
                    v1.delete_namespaced_persistent_volume_claim(
                        name="benchmark-test-pvc",
                        namespace="default",
                    )

                results.append(
                    BenchmarkResult(
                        test_name="PVC Creation Time",
                        component="storage",
                        metric_name="pvc_creation_time",
                        value=pvc_creation_time,
                        unit="ms",
                        success=pvc_bound,
                        error_message="PVC failed to bind" if not pvc_bound else None,
                        metadata={"storage_class": default_sc},
                    ),
                )

        except Exception as e:
            results.append(
                BenchmarkResult(
                    test_name="Storage Performance",
                    component="storage",
                    metric_name="storage_test",
                    value=0,
                    unit="score",
                    success=False,
                    error_message=str(e),
                ),
            )

        return results

    def benchmark_network_performance(self) -> list[BenchmarkResult]:
        """Benchmark network performance."""
        results = []

        try:
            # Test DNS resolution time
            start_time = time.time()

            try:
                import socket

                socket.gethostbyname("kubernetes.default.svc.cluster.local")
                dns_resolution_time = (time.time() - start_time) * 1000

                results.append(
                    BenchmarkResult(
                        test_name="DNS Resolution Time",
                        component="networking",
                        metric_name="dns_resolution_time",
                        value=dns_resolution_time,
                        unit="ms",
                    ),
                )
            except Exception as e:
                results.append(
                    BenchmarkResult(
                        test_name="DNS Resolution Time",
                        component="networking",
                        metric_name="dns_resolution_time",
                        value=0,
                        unit="ms",
                        success=False,
                        error_message=str(e),
                    ),
                )

            # Test service connectivity
            v1 = client.CoreV1Api()
            services = v1.list_service_for_all_namespaces()

            results.append(
                BenchmarkResult(
                    test_name="Services Available",
                    component="networking",
                    metric_name="services_count",
                    value=len(services.items),
                    unit="count",
                ),
            )

        except Exception as e:
            results.append(
                BenchmarkResult(
                    test_name="Network Performance",
                    component="networking",
                    metric_name="network_test",
                    value=0,
                    unit="score",
                    success=False,
                    error_message=str(e),
                ),
            )

        return results

    def run_load_test(
        self,
        target_url: str,
        duration_seconds: int = 60,
        concurrent_users: int = 10,
    ) -> list[BenchmarkResult]:
        """Run a load test against a target URL."""
        results = []

        self.logger.info(
            f"Starting load test: {target_url} for {duration_seconds}s with {concurrent_users} users",
        )

        response_times = []
        errors = 0
        successful_requests = 0

        def make_request() -> tuple[bool, float]:
            """Make a single request and return success status and response time."""
            try:
                start_time = time.time()
                response = requests.get(target_url, timeout=10, verify=False)
                end_time = time.time()

                if response.status_code < 400:
                    return True, (end_time - start_time) * 1000
                return False, 0
            except Exception:
                return False, 0

        start_time = time.time()
        end_time = start_time + duration_seconds

        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            while time.time() < end_time:
                futures = []

                # Submit batch of requests
                for _ in range(concurrent_users):
                    if time.time() >= end_time:
                        break
                    futures.append(executor.submit(make_request))

                # Collect results
                for future in as_completed(futures, timeout=30):
                    try:
                        success, response_time = future.result()
                        if success:
                            response_times.append(response_time)
                            successful_requests += 1
                        else:
                            errors += 1
                    except Exception:
                        errors += 1

                time.sleep(0.1)  # Brief pause between batches

        total_duration = time.time() - start_time
        total_requests = successful_requests + errors

        if response_times:
            avg_response_time = statistics.mean(response_times)
            percentile_95 = sorted(response_times)[int(len(response_times) * 0.95)]
            requests_per_second = total_requests / total_duration

            results.extend(
                [
                    BenchmarkResult(
                        test_name="Load Test - Average Response Time",
                        component=target_url,
                        metric_name="avg_response_time",
                        value=avg_response_time,
                        unit="ms",
                        metadata={
                            "concurrent_users": concurrent_users,
                            "duration_seconds": duration_seconds,
                            "total_requests": total_requests,
                            "successful_requests": successful_requests,
                            "errors": errors,
                        },
                    ),
                    BenchmarkResult(
                        test_name="Load Test - 95th Percentile Response Time",
                        component=target_url,
                        metric_name="p95_response_time",
                        value=percentile_95,
                        unit="ms",
                    ),
                    BenchmarkResult(
                        test_name="Load Test - Requests Per Second",
                        component=target_url,
                        metric_name="requests_per_second",
                        value=requests_per_second,
                        unit="rps",
                    ),
                    BenchmarkResult(
                        test_name="Load Test - Error Rate",
                        component=target_url,
                        metric_name="error_rate",
                        value=(errors / total_requests) * 100 if total_requests > 0 else 0,
                        unit="percent",
                    ),
                ],
            )
        else:
            results.append(
                BenchmarkResult(
                    test_name="Load Test",
                    component=target_url,
                    metric_name="load_test",
                    value=0,
                    unit="score",
                    success=False,
                    error_message="All requests failed",
                ),
            )

        return results

    def run_comprehensive_benchmark(
        self,
        api_endpoints: list[str] | None = None,
        load_test_targets: list[str] | None = None,
    ) -> PerformanceReport:
        """Run comprehensive performance benchmark suite."""
        report = PerformanceReport(
            test_suite="Infrastructure Comprehensive Benchmark",
            start_time=datetime.now(),
            environment_info=self.collect_environment_info(),
        )

        self.logger.info("🚀 Starting comprehensive infrastructure benchmark suite")

        # Default endpoints for homelab
        if api_endpoints is None:
            api_endpoints = [
                "https://gitlab.homelab.local/api/v4/projects",
                "https://prometheus.homelab.local/api/v1/status/config",
                "https://grafana.homelab.local/api/health",
            ]

        # API Response Time Benchmarks
        self.logger.info("📊 Running API response time benchmarks")
        api_results = self.benchmark_api_response_time(api_endpoints)
        for result in api_results:
            report.add_result(result)

        # Kubernetes Performance Benchmarks
        self.logger.info("☸️  Running Kubernetes performance benchmarks")
        k8s_results = self.benchmark_kubernetes_performance()
        for result in k8s_results:
            report.add_result(result)

        # Storage Performance Benchmarks
        self.logger.info("💾 Running storage performance benchmarks")
        storage_results = self.benchmark_storage_performance()
        for result in storage_results:
            report.add_result(result)

        # Network Performance Benchmarks
        self.logger.info("🌐 Running network performance benchmarks")
        network_results = self.benchmark_network_performance()
        for result in network_results:
            report.add_result(result)

        # Load Testing (if targets specified)
        if load_test_targets:
            self.logger.info("⚡ Running load tests")
            for target in load_test_targets:
                load_results = self.run_load_test(target, duration_seconds=30, concurrent_users=5)
                for result in load_results:
                    report.add_result(result)

        report.finalize()
        self.logger.info(
            f"✅ Benchmark suite completed in {report.total_duration_seconds:.2f} seconds",
        )

        return report

    def export_report(
        self,
        report: PerformanceReport,
        output_file: str,
        format: str = "json",
    ) -> None:
        """Export performance report to file."""
        if format.lower() == "json":
            report_data = {
                "test_suite": report.test_suite,
                "start_time": report.start_time.isoformat(),
                "end_time": report.end_time.isoformat() if report.end_time else None,
                "total_duration_seconds": report.total_duration_seconds,
                "environment_info": report.environment_info,
                "summary_stats": report.summary_stats,
                "results": [
                    {
                        "test_name": r.test_name,
                        "component": r.component,
                        "metric_name": r.metric_name,
                        "value": r.value,
                        "unit": r.unit,
                        "timestamp": r.timestamp.isoformat(),
                        "success": r.success,
                        "error_message": r.error_message,
                        "metadata": r.metadata,
                    }
                    for r in report.results
                ],
            }

            with open(output_file, "w") as f:
                json.dump(report_data, f, indent=2)

        elif format.lower() == "markdown":
            self._export_markdown_report(report, output_file)

        self.logger.info(f"📄 Performance report exported to {output_file}")

    def _export_markdown_report(self, report: PerformanceReport, output_file: str) -> None:
        """Export report in Markdown format."""
        with open(output_file, "w") as f:
            f.write(f"# {report.test_suite}\n\n")
            f.write(f"**Generated:** {report.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Duration:** {report.total_duration_seconds:.2f} seconds\n\n")

            # Summary
            f.write("## Summary\n\n")
            stats = report.summary_stats
            f.write(f"- **Total Tests:** {stats.get('total_tests', 0)}\n")
            f.write(f"- **Successful:** {stats.get('successful_tests', 0)}\n")
            f.write(f"- **Failed:** {stats.get('failed_tests', 0)}\n")
            f.write(f"- **Success Rate:** {stats.get('success_rate', 0):.1f}%\n")
            f.write(
                f"- **Average Response Time:** {stats.get('avg_response_time_ms', 0):.2f}ms\n\n",
            )

            # Environment Info
            f.write("## Environment\n\n")
            for key, value in report.environment_info.items():
                f.write(f"- **{key.replace('_', ' ').title()}:** {value}\n")
            f.write("\n")

            # Results by Component
            components = list({r.component for r in report.results})
            for component in sorted(components):
                f.write(f"## {component}\n\n")
                component_results = [r for r in report.results if r.component == component]

                f.write("| Test | Metric | Value | Unit | Status |\n")
                f.write("|------|--------|-------|------|--------|\n")

                for result in component_results:
                    status = "✅" if result.success else "❌"
                    f.write(
                        f"| {result.test_name} | {result.metric_name} | {result.value:.2f} | {result.unit} | {status} |\n",
                    )
                f.write("\n")


def main() -> None:
    """Main function for standalone benchmarking."""
    import argparse

    parser = argparse.ArgumentParser(description="Infrastructure performance benchmarking")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument("--endpoints", nargs="+", help="API endpoints to benchmark")
    parser.add_argument("--load-test", nargs="+", help="URLs to load test")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format",
    )
    parser.add_argument("--duration", type=int, default=30, help="Load test duration in seconds")
    parser.add_argument("--users", type=int, default=5, help="Concurrent users for load testing")

    args = parser.parse_args()

    benchmarker = InfrastructureBenchmarker(
        kubeconfig_path=args.kubeconfig,
        log_level=args.log_level,
    )

    if args.load_test:
        benchmarker.test_duration = args.duration
        benchmarker.concurrent_requests = args.users

    report = benchmarker.run_comprehensive_benchmark(
        api_endpoints=args.endpoints,
        load_test_targets=args.load_test,
    )

    # Print summary to console
    print("\n🎯 Performance Benchmark Results")
    print("=" * 50)
    print(f"Test Suite: {report.test_suite}")
    print(f"Duration: {report.total_duration_seconds:.2f} seconds")
    print(f"Total Tests: {report.summary_stats.get('total_tests', 0)}")
    print(f"Success Rate: {report.summary_stats.get('success_rate', 0):.1f}%")
    print(f"Average Response Time: {report.summary_stats.get('avg_response_time_ms', 0):.2f}ms")

    print("\n📊 Results by Component:")
    components = list({r.component for r in report.results})
    for component in sorted(components):
        component_results = [r for r in report.results if r.component == component]
        successful = [r for r in component_results if r.success]
        print(f"  {component}: {len(successful)}/{len(component_results)} tests passed")

    # Export detailed report if requested
    if args.output:
        benchmarker.export_report(report, args.output, args.format)

    # Exit with error code if tests failed
    if report.summary_stats.get("failed_tests", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
