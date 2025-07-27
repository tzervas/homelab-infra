#!/usr/bin/env python3
"""Rootless Compatibility Checker for Homelab Infrastructure.

This module specifically validates that the homelab deployment is properly
configured for rootless operation with appropriate security contexts.
"""

from dataclasses import dataclass, field
import logging
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException

    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False

try:
    from .common import safe_import, setup_logger
    from .network_security import SecurityStatus
except ImportError:
    # Fallback imports
    def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    @dataclass
    class SecurityStatus:
        check_type: str
        component: str
        status: str
        message: str
        details: Dict[str, Any] = field(default_factory=dict)
        recommendations: List[str] = field(default_factory=list)

        @property
        def is_secure(self) -> bool:
            return self.status == "secure"


@dataclass
class RootlessCompatibilityResult:
    """Result of rootless compatibility check."""

    component: str
    compatible: bool
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class RootlessCompatibilityChecker:
    """Validates homelab configuration for rootless deployment compatibility."""

    def __init__(self, kubeconfig_path: Optional[str] = None, log_level: str = "INFO") -> None:
        """Initialize the rootless compatibility checker."""
        self.logger = setup_logger(__name__, log_level)
        self.k8s_client = None
        self.project_root = Path(__file__).parent.parent.parent

        # Deployment user configuration
        self.deployment_user = os.getenv("HOMELAB_USER", "homelab-deploy")
        self.deployment_home = f"/home/{self.deployment_user}"

        # Deployment architecture detection
        self.bastion_host = os.getenv("HOMELAB_SERVER_IP", "192.168.16.26")
        self.bastion_user = os.getenv("HOMELAB_SSH_USER", "kang")
        self.deployment_mode = os.getenv(
            "HOMELAB_DEPLOYMENT_MODE", "vm-based"
        )  # vm-based or bare-metal

        # Auto-detect deployment architecture
        self._detect_deployment_architecture()

        if KUBERNETES_AVAILABLE:
            self._init_kubernetes_client(kubeconfig_path)

    def _detect_deployment_architecture(self) -> None:
        """Auto-detect deployment architecture (VM-based vs bare-metal)."""
        try:
            # Check if deployment mode is explicitly set via environment variable
            env_mode = os.getenv("HOMELAB_DEPLOYMENT_MODE")
            if env_mode:
                self.deployment_mode = env_mode
                self.logger.info(f"Using explicit deployment mode from environment: {env_mode}")
                return

            # Check if we're running on a VM guest (detect virtualization)
            if Path("/proc/cpuinfo").exists():
                with open("/proc/cpuinfo") as f:
                    cpuinfo = f.read()
                    if any(
                        virt in cpuinfo.lower()
                        for virt in ["kvm", "qemu", "hypervisor", "virtualization"]
                    ):
                        self.deployment_mode = "vm-guest"
                        self.logger.info("Detected VM guest environment")
                        return

            # Check if we're on the bastion host (has libvirt/KVM capabilities)
            if subprocess.run(["which", "virsh"], capture_output=True, check=False).returncode == 0:
                # Check if VMs exist for cluster
                result = subprocess.run(
                    ["virsh", "list", "--all"], capture_output=True, text=True, check=False
                )
                if result.returncode == 0 and "test-vm" in result.stdout:
                    self.deployment_mode = "vm-based"
                    self.logger.info("Detected VM-based deployment on bastion host")
                    return

            # Check network interfaces for bastion detection
            try:
                import socket

                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                if local_ip.startswith("192.168.16."):
                    self.deployment_mode = "bastion-host"
                    self.logger.info("Detected bastion host environment")
                elif local_ip.startswith("192.168.122."):
                    self.deployment_mode = "vm-guest"
                    self.logger.info("Detected VM guest on libvirt network")
                else:
                    self.deployment_mode = "bare-metal"
                    self.logger.info("Detected bare-metal deployment")
            except:
                pass

        except Exception as e:
            self.logger.debug(f"Architecture detection failed: {e}")
            self.deployment_mode = "unknown"

    def _init_kubernetes_client(self, kubeconfig_path: Optional[str]) -> None:
        """Initialize Kubernetes API client with architecture-aware logic."""
        try:
            if kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
            elif self.deployment_mode == "vm-guest":
                # On VM guest, try local kubeconfig first
                config.load_kube_config()
            elif self.deployment_mode in ["bastion-host", "vm-based"]:
                # On bastion, may need to connect through VM
                self.logger.info("Bastion host detected - K8s access may require VM connection")
                try:
                    config.load_kube_config()
                except:
                    self.logger.warning(
                        "No direct K8s access from bastion - normal for VM-based deployment"
                    )
                    return
            else:
                config.load_kube_config()

            self.k8s_client = client.ApiClient()
            self.logger.info(f"Kubernetes client initialized for {self.deployment_mode} deployment")
        except Exception as e:
            self.logger.warning(f"Could not initialize Kubernetes client: {e}")

    def check_deployment_user_configuration(self) -> RootlessCompatibilityResult:
        """Check if deployment user is properly configured."""
        issues = []
        recommendations = []
        details = {}

        try:
            # Check if deployment user exists
            result = subprocess.run(
                ["id", self.deployment_user], capture_output=True, text=True, check=False
            )

            if result.returncode != 0:
                issues.append(f"Deployment user {self.deployment_user} does not exist")
                recommendations.append(
                    "Run setup-secure-deployment.sh to create the deployment user"
                )
            else:
                details["user_info"] = result.stdout.strip()
                self.logger.debug(f"Deployment user info: {result.stdout.strip()}")

            # Check home directory structure
            required_dirs = [
                f"{self.deployment_home}/.ssh",
                f"{self.deployment_home}/.kube",
                f"{self.deployment_home}/.local/bin",
                f"{self.deployment_home}/.credentials",
            ]

            missing_dirs = []
            for dir_path in required_dirs:
                if not os.path.exists(dir_path):
                    missing_dirs.append(dir_path)

            if missing_dirs:
                issues.extend([f"Missing directory: {d}" for d in missing_dirs])
                recommendations.append("Ensure deployment user directories are properly created")

            # Check environment configuration
            env_file = f"{self.deployment_home}/.environment"
            if not os.path.exists(env_file):
                issues.append(f"Environment file {env_file} not found")
                recommendations.append("Create .environment file with proper configuration")

            # Check sudo configuration
            sudoers_file = f"/etc/sudoers.d/{self.deployment_user}"
            if not os.path.exists(sudoers_file):
                issues.append(f"Sudoers file {sudoers_file} not found")
                recommendations.append("Configure sudo access for deployment user")

        except Exception as e:
            issues.append(f"Error checking deployment user: {e}")
            recommendations.append("Verify system access and permissions")

        return RootlessCompatibilityResult(
            component="deployment_user",
            compatible=len(issues) == 0,
            issues=issues,
            recommendations=recommendations,
            details=details,
        )

    def check_ansible_configuration(self) -> RootlessCompatibilityResult:
        """Check Ansible configuration for rootless deployment."""
        issues = []
        recommendations = []
        details = {}

        try:
            ansible_cfg = self.project_root / "ansible" / "ansible.cfg"

            if not ansible_cfg.exists():
                issues.append("ansible.cfg not found")
                recommendations.append("Ensure ansible.cfg is properly configured")
                return RootlessCompatibilityResult(
                    component="ansible_config",
                    compatible=False,
                    issues=issues,
                    recommendations=recommendations,
                )

            # Read and validate ansible.cfg
            with open(ansible_cfg) as f:
                config_content = f.read()

            # Check for proper privilege escalation settings
            if "become = False" not in config_content:
                issues.append("Default become should be False in ansible.cfg")
                recommendations.append("Set become = False in [privilege_escalation] section")

            if "become_ask_pass = False" not in config_content:
                issues.append("become_ask_pass should be False for passwordless sudo")
                recommendations.append("Configure passwordless sudo for deployment user")

            # Check for deployment user as remote_user
            if f"remote_user = {self.deployment_user}" not in config_content:
                details["current_remote_user"] = "Check ansible.cfg for remote_user setting"
                recommendations.append(f"Consider using {self.deployment_user} as remote_user")

            # Check privilege configuration file
            privilege_yml = self.project_root / "ansible" / "group_vars" / "all" / "privilege.yml"
            if not privilege_yml.exists():
                issues.append("privilege.yml configuration not found")
                recommendations.append("Create privilege.yml with rootless deployment settings")

        except Exception as e:
            issues.append(f"Error checking Ansible configuration: {e}")
            recommendations.append("Verify Ansible configuration files")

        return RootlessCompatibilityResult(
            component="ansible_config",
            compatible=len(issues) == 0,
            issues=issues,
            recommendations=recommendations,
            details=details,
        )

    def check_kubernetes_security_contexts(self) -> RootlessCompatibilityResult:
        """Check Kubernetes deployments for proper security contexts."""
        issues = []
        recommendations = []
        details = {}

        if not self.k8s_client:
            return RootlessCompatibilityResult(
                component="kubernetes_security",
                compatible=False,
                issues=["Kubernetes client not available"],
                recommendations=["Ensure kubeconfig is properly configured"],
            )

        try:
            apps_v1 = client.AppsV1Api(self.k8s_client)
            v1 = client.CoreV1Api(self.k8s_client)

            # Check deployments for security contexts with comprehensive counting
            deployments = apps_v1.list_deployment_for_all_namespaces()
            privileged_deployments = []
            missing_security_contexts = []

            for deployment in deployments.items:
                # Skip system namespaces that may need special permissions
                if deployment.metadata.namespace in ["kube-system", "metallb-system"]:
                    continue

                deployment_name = f"{deployment.metadata.namespace}/{deployment.metadata.name}"
                spec = deployment.spec.template.spec

                # Check pod security context
                if not spec.security_context:
                    missing_security_contexts.append(f"{deployment_name} (pod level)")
                elif spec.security_context.run_as_non_root is not True:
                    privileged_deployments.append(f"{deployment_name} (pod level)")

                # Check container security contexts
                for container in spec.containers or []:
                    container_ref = f"{deployment_name}:{container.name}"
                    if container.security_context:
                        if (
                            container.security_context.run_as_user == 0
                            or container.security_context.privileged is True
                        ):
                            privileged_deployments.append(container_ref)
                    else:
                        missing_security_contexts.append(container_ref)

            total_privileged = len(privileged_deployments)
            total_missing = len(missing_security_contexts)

            details["total_deployments"] = len(deployments.items)
            details["total_privileged_deployments"] = total_privileged
            details["total_missing_security_contexts"] = total_missing
            details["privileged_deployments_sample"] = privileged_deployments[:5]
            details["missing_security_contexts_sample"] = missing_security_contexts[:5]

            if total_privileged > 0:
                issues.append(
                    f"Found {total_privileged} deployments/containers with privileged access"
                )
                if total_privileged > 5:
                    issues.append(f"Showing 5 examples: {', '.join(privileged_deployments[:5])}")
                recommendations.extend(
                    [
                        f"Fix {total_privileged} privileged containers",
                        "Set runAsNonRoot: true in pod security contexts",
                        "Use non-zero runAsUser values",
                        "Update Helm values files with proper security contexts",
                    ]
                )

            if total_missing > 0:
                issues.append(
                    f"Found {total_missing} deployments/containers without security contexts"
                )
                if total_missing > 5:
                    issues.append(f"Showing 5 examples: {', '.join(missing_security_contexts[:5])}")
                recommendations.extend(
                    [
                        f"Add security contexts to {total_missing} containers/pods",
                        "Add security contexts to all pod specifications",
                    ]
                )

            # Check Pod Security Standards with comprehensive counting
            namespaces = v1.list_namespace()
            namespaces_without_pss = []

            for namespace in namespaces.items:
                # Skip system namespaces
                if namespace.metadata.name.startswith("kube-"):
                    continue

                labels = namespace.metadata.labels or {}
                has_pss = any(label.startswith("pod-security.kubernetes.io/") for label in labels)

                if not has_pss:
                    namespaces_without_pss.append(namespace.metadata.name)

            total_pss_missing = len(namespaces_without_pss)

            if total_pss_missing > 0:
                issues.append(
                    f"Found {total_pss_missing} namespaces without Pod Security Standards"
                )
                if total_pss_missing > 5:
                    issues.append(
                        f"Missing PSS namespaces (showing 5): {', '.join(namespaces_without_pss[:5])}"
                    )
                recommendations.extend(
                    [
                        f"Configure Pod Security Standards for {total_pss_missing} namespaces",
                        "Apply Pod Security Standards to all namespaces",
                    ]
                )
                details["total_namespaces_without_pss"] = total_pss_missing
                details["namespaces_without_pss_sample"] = namespaces_without_pss[:5]

        except Exception as e:
            issues.append(f"Error checking Kubernetes security contexts: {e}")
            recommendations.append("Verify Kubernetes cluster access")

        return RootlessCompatibilityResult(
            component="kubernetes_security",
            compatible=len(issues) == 0,
            issues=issues,
            recommendations=recommendations,
            details=details,
        )

    def check_helm_values_security(self) -> RootlessCompatibilityResult:
        """Check Helm values files for security context configurations."""
        issues = []
        recommendations = []
        details = {}

        try:
            # Find all Helm values files
            values_files = []
            for pattern in ["**/values*.yaml", "**/values*.yml"]:
                values_files.extend(self.project_root.glob(pattern))

            files_without_security = []
            security_context_patterns = ["runAsNonRoot", "runAsUser", "securityContext", "fsGroup"]

            for values_file in values_files:
                try:
                    # Skip template files and examples
                    if any(
                        skip in str(values_file) for skip in ["template", "example", ".template"]
                    ):
                        continue

                    with open(values_file) as f:
                        content = f.read()

                    has_security_config = any(
                        pattern in content for pattern in security_context_patterns
                    )

                    if not has_security_config:
                        relative_path = values_file.relative_to(self.project_root)
                        files_without_security.append(str(relative_path))

                except Exception as e:
                    self.logger.warning(f"Error reading {values_file}: {e}")

            total_files_without_security = len(files_without_security)

            details["total_values_files"] = len(values_files)
            details["total_files_without_security"] = total_files_without_security
            details["files_without_security_sample"] = files_without_security[:5]

            if total_files_without_security > 0:
                issues.append(
                    f"Found {total_files_without_security} Helm values files without security contexts"
                )
                if total_files_without_security > 5:
                    issues.append(
                        f"Files missing security contexts (showing 5): {', '.join(files_without_security[:5])}"
                    )
                recommendations.extend(
                    [
                        f"Add security contexts to {total_files_without_security} Helm values files",
                        "Add security contexts to all Helm values files",
                        "Use global security context configuration",
                        "Ensure runAsNonRoot: true is set for all components",
                    ]
                )

        except Exception as e:
            issues.append(f"Error checking Helm values files: {e}")
            recommendations.append("Verify Helm configuration files")

        return RootlessCompatibilityResult(
            component="helm_values",
            compatible=len(issues) == 0,
            issues=issues,
            recommendations=recommendations,
            details=details,
        )

    def check_testing_framework_compatibility(self) -> RootlessCompatibilityResult:
        """Check if testing framework can run without root privileges."""
        issues = []
        recommendations = []
        details = {}

        try:
            # Check if testing scripts can be executed by deployment user
            testing_dir = self.project_root / "scripts" / "testing"

            if not testing_dir.exists():
                issues.append("Testing directory not found")
                recommendations.append("Ensure testing framework is properly installed")
                return RootlessCompatibilityResult(
                    component="testing_framework",
                    compatible=False,
                    issues=issues,
                    recommendations=recommendations,
                )

            # Check Python dependencies
            try:
                import kubernetes

                details["kubernetes_client"] = "available"
            except ImportError:
                issues.append("Kubernetes Python client not available")
                recommendations.append("Install kubernetes Python package")

            # Check if testing scripts are executable
            test_scripts = list(testing_dir.glob("*.py"))
            non_executable = []

            for script in test_scripts:
                if not os.access(script, os.X_OK):
                    non_executable.append(script.name)

            if non_executable:
                issues.append(f"Found {len(non_executable)} non-executable test scripts")
                recommendations.append("Make testing scripts executable")
                details["non_executable_scripts"] = non_executable

            # Check configuration compatibility
            config_file = testing_dir / "config.py"
            if config_file.exists():
                try:
                    with open(config_file) as f:
                        config_content = f.read()

                    if "verify_ssl" not in config_content:
                        recommendations.append("Consider adding SSL verification configuration")

                    details["config_file"] = "found"
                except Exception as e:
                    issues.append(f"Error reading config file: {e}")

        except Exception as e:
            issues.append(f"Error checking testing framework: {e}")
            recommendations.append("Verify testing framework installation")

        return RootlessCompatibilityResult(
            component="testing_framework",
            compatible=len(issues) == 0,
            issues=issues,
            recommendations=recommendations,
            details=details,
        )

    def check_vm_deployment_readiness(self) -> RootlessCompatibilityResult:
        """Check VM-based deployment readiness (for bastion hosts)."""
        issues = []
        recommendations = []
        details = {}

        if self.deployment_mode not in ["bastion-host", "vm-based"]:
            return RootlessCompatibilityResult(
                component="vm_deployment",
                compatible=True,
                issues=[],
                recommendations=[],
                details={"deployment_mode": self.deployment_mode, "vm_checks": "not_applicable"},
            )

        try:
            # Check libvirt/KVM availability
            virsh_result = subprocess.run(["which", "virsh"], capture_output=True, check=False)
            if virsh_result.returncode != 0:
                issues.append("virsh command not available - libvirt not installed")
                recommendations.append("Install libvirt and KVM packages")
            else:
                details["libvirt"] = "available"

                # Check if libvirt daemon is running
                systemctl_result = subprocess.run(
                    ["systemctl", "is-active", "libvirtd"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if systemctl_result.returncode != 0:
                    issues.append("libvirtd service not running")
                    recommendations.append("Start and enable libvirtd service")
                else:
                    details["libvirtd"] = "running"

                # Check default network
                net_list_result = subprocess.run(
                    ["virsh", "net-list", "--all"], capture_output=True, text=True, check=False
                )
                if net_list_result.returncode == 0:
                    if "default" not in net_list_result.stdout:
                        issues.append("Default libvirt network not available")
                        recommendations.append("Create and start default libvirt network")
                    elif "active" not in net_list_result.stdout:
                        issues.append("Default libvirt network not active")
                        recommendations.append("Start default libvirt network")
                    else:
                        details["default_network"] = "active"

                # Check existing VMs
                vm_list_result = subprocess.run(
                    ["virsh", "list", "--all"], capture_output=True, text=True, check=False
                )
                if vm_list_result.returncode == 0:
                    vm_count = len(
                        [line for line in vm_list_result.stdout.split("\n") if "test-vm" in line]
                    )
                    details["existing_vms"] = vm_count

                    if vm_count > 0:
                        details["cluster_vms"] = "found"
                        # Check if test VM is running
                        if "running" in vm_list_result.stdout:
                            details["cluster_status"] = "running"
                        else:
                            details["cluster_status"] = "stopped"
                            recommendations.append("Start cluster VMs for testing")

            # Check user permissions for libvirt
            try:
                groups_result = subprocess.run(
                    ["groups"], capture_output=True, text=True, check=False
                )
                if "libvirt" not in groups_result.stdout:
                    issues.append("Current user not in libvirt group")
                    recommendations.append("Add user to libvirt group and re-login")
                else:
                    details["user_libvirt_access"] = "granted"
            except:
                pass

            # Check bridge networking
            ip_result = subprocess.run(
                ["ip", "addr", "show", "virbr0"], capture_output=True, text=True, check=False
            )
            if ip_result.returncode != 0:
                issues.append("virbr0 bridge interface not found")
                recommendations.append("Ensure libvirt default network creates virbr0 bridge")
            else:
                details["bridge_network"] = "available"
                # Extract bridge IP
                import re

                ip_match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", ip_result.stdout)
                if ip_match:
                    details["bridge_ip"] = ip_match.group(1)

        except Exception as e:
            issues.append(f"Error checking VM deployment readiness: {e}")
            recommendations.append("Verify libvirt/KVM installation and configuration")

        return RootlessCompatibilityResult(
            component="vm_deployment",
            compatible=len(issues) == 0,
            issues=issues,
            recommendations=recommendations,
            details=details,
        )

    def check_cluster_connectivity(self) -> RootlessCompatibilityResult:
        """Check Kubernetes cluster connectivity with architecture awareness."""
        issues = []
        recommendations = []
        details = {}

        details["deployment_mode"] = self.deployment_mode

        # Architecture-specific connectivity checks
        if self.deployment_mode == "vm-guest":
            # Running on VM guest - should have direct k8s access
            if not self.k8s_client:
                issues.append("Kubernetes client not initialized on VM guest")
                recommendations.append("Ensure kubeconfig is available on VM")
            else:
                details["k8s_access"] = "direct_from_vm"

        elif self.deployment_mode in ["bastion-host", "vm-based"]:
            # Running on bastion - may need ProxyJump to access k8s
            if not self.k8s_client:
                issues.append("No direct Kubernetes access from bastion host")
                recommendations.extend(
                    [
                        "This is normal for VM-based deployments",
                        "Access cluster via SSH to VM guest",
                        "Use ProxyJump for kubectl commands",
                    ]
                )
                details["k8s_access"] = "requires_vm_connection"
            else:
                # Unexpected direct access from bastion
                details["k8s_access"] = "direct_from_bastion"

        elif self.deployment_mode == "bare-metal":
            # Bare metal - should have direct access
            if not self.k8s_client:
                issues.append("Kubernetes cluster not accessible")
                recommendations.extend(
                    [
                        "Check if K3s cluster is running",
                        "Verify kubeconfig file exists and is valid",
                        "Ensure cluster API server is accessible",
                    ]
                )
            else:
                details["k8s_access"] = "direct_bare_metal"

        # If we have a client, test actual connectivity
        if self.k8s_client:
            try:
                v1 = client.CoreV1Api(self.k8s_client)
                nodes = v1.list_node(timeout_seconds=10)
                details["node_count"] = len(nodes.items)
                details["cluster_reachable"] = True

                # Check node readiness
                ready_nodes = sum(
                    1
                    for node in nodes.items
                    if any(
                        condition.type == "Ready" and condition.status == "True"
                        for condition in node.status.conditions
                    )
                )
                details["ready_nodes"] = ready_nodes

                if ready_nodes == 0:
                    issues.append("No nodes are in Ready state")
                    recommendations.append("Check node health and troubleshoot cluster issues")

            except Exception as e:
                issues.append(f"Cluster connectivity test failed: {e}")
                recommendations.append("Verify cluster is healthy and accessible")
                details["cluster_reachable"] = False

        return RootlessCompatibilityResult(
            component="cluster_connectivity",
            compatible=len(issues) == 0 or self.deployment_mode in ["bastion-host", "vm-based"],
            issues=issues,
            recommendations=recommendations,
            details=details,
        )

    def run_comprehensive_compatibility_check(self) -> List[RootlessCompatibilityResult]:
        """Run all rootless compatibility checks with auto-switching based on deployment architecture."""
        self.logger.info(
            f"Starting comprehensive rootless compatibility check for {self.deployment_mode} deployment..."
        )

        # Base checks that apply to all deployment modes
        base_checks = [
            self.check_deployment_user_configuration,
            self.check_ansible_configuration,
            self.check_helm_values_security,
            self.check_testing_framework_compatibility,
        ]

        # Architecture-specific checks
        architecture_specific_checks = []

        if self.deployment_mode in ["bastion-host", "vm-based"]:
            # VM-based deployment checks
            architecture_specific_checks.extend(
                [self.check_vm_deployment_readiness, self.check_cluster_connectivity]
            )
            self.logger.info("Running VM-based deployment checks...")

        elif self.deployment_mode == "vm-guest":
            # Running on VM guest - check cluster directly
            architecture_specific_checks.extend(
                [self.check_kubernetes_security_contexts, self.check_cluster_connectivity]
            )
            self.logger.info("Running VM guest deployment checks...")

        elif self.deployment_mode == "bare-metal":
            # Bare metal deployment
            architecture_specific_checks.extend(
                [self.check_kubernetes_security_contexts, self.check_cluster_connectivity]
            )
            self.logger.info("Running bare-metal deployment checks...")

        else:
            # Unknown deployment mode - run all checks
            architecture_specific_checks.extend(
                [
                    self.check_kubernetes_security_contexts,
                    self.check_vm_deployment_readiness,
                    self.check_cluster_connectivity,
                ]
            )
            self.logger.warning(
                f"Unknown deployment mode '{self.deployment_mode}' - running all checks"
            )

        # Combine all checks
        checks = base_checks + architecture_specific_checks

        results = []
        for check in checks:
            try:
                result = check()
                results.append(result)

                status_icon = "✅" if result.compatible else "❌"
                self.logger.info(
                    f"{status_icon} {result.component}: {'Compatible' if result.compatible else 'Issues found'}"
                )

                if result.issues:
                    for issue in result.issues[:3]:  # Show first 3 issues
                        self.logger.warning(f"  - {issue}")

            except Exception as e:
                self.logger.exception(f"Compatibility check failed: {e}")
                results.append(
                    RootlessCompatibilityResult(
                        component="unknown",
                        compatible=False,
                        issues=[f"Check failed: {e!s}"],
                        recommendations=["Investigate the error and retry"],
                    )
                )

        return results

    def generate_compatibility_report(self, results: List[RootlessCompatibilityResult]) -> str:
        """Generate a comprehensive compatibility report."""
        compatible_count = sum(1 for r in results if r.compatible)
        total_count = len(results)

        report = f"""
# Rootless Deployment Compatibility Report

## Deployment Architecture
- **Detected Mode**: {self.deployment_mode}
- **Bastion Host**: {self.bastion_host}
- **Deployment User**: {self.deployment_user}

## Summary
- **Compatible Components**: {compatible_count}/{total_count}
- **Overall Status**: {'✅ Ready for rootless deployment' if compatible_count == total_count else '❌ Issues need to be resolved'}

## Component Details

"""

        for result in results:
            status = "✅ Compatible" if result.compatible else "❌ Issues Found"
            report += f"### {result.component.replace('_', ' ').title()}\n"
            report += f"**Status**: {status}\n\n"

            if result.issues:
                report += "**Issues**:\n"
                for issue in result.issues:
                    report += f"- {issue}\n"
                report += "\n"

            if result.recommendations:
                report += "**Recommendations**:\n"
                for rec in result.recommendations:
                    report += f"- {rec}\n"
                report += "\n"

        if compatible_count < total_count:
            report += f"""
## Next Steps

### For {self.deployment_mode.title()} Deployment:
"""

            if self.deployment_mode in ["bastion-host", "vm-based"]:
                report += """
1. **VM Infrastructure Setup**:
   - Install libvirt/KVM packages if missing
   - Start libvirtd service and default network
   - Create test VMs using Ansible playbooks

2. **Deployment User Setup**:
   - Run setup-secure-deployment.sh on bastion host
   - Ensure deployment user has libvirt group membership

3. **VM Deployment Process**:
   - Use ansible-playbook site.yml with phase=vm-test
   - Deploy K3s cluster on created VMs
   - Access cluster via ProxyJump to VMs
"""
            elif self.deployment_mode == "vm-guest":
                report += """
1. **VM Guest Configuration**:
   - Ensure kubeconfig is properly configured
   - Verify deployment user permissions
   - Install required tools (kubectl, helm)

2. **Cluster Access**:
   - Test direct cluster connectivity
   - Deploy applications with security contexts
"""
            elif self.deployment_mode == "bare-metal":
                report += """
1. **Bare Metal Setup**:
   - Install K3s directly on server
   - Configure deployment user permissions
   - Ensure cluster API server is accessible

2. **Direct Deployment**:
   - Use traditional deployment methods
   - Apply security contexts directly
"""

            report += """
### General Steps:
4. Address the issues listed above in order of priority
5. Re-run the compatibility check after making changes
6. Update Helm values files with proper security contexts
7. Test deployment with the rootless user

For detailed guidance, see the rootless deployment documentation.
"""

        return report


def main() -> None:
    """Main function for standalone testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Check rootless deployment compatibility")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARN", "ERROR"])
    parser.add_argument("--output", help="Output file for report")
    parser.add_argument("--deployment-user", help="Deployment user name", default="homelab-deploy")
    parser.add_argument(
        "--deployment-mode",
        choices=["auto", "bare-metal", "bastion-host", "vm-based", "vm-guest"],
        default="auto",
        help="Force specific deployment mode instead of auto-detection",
    )
    parser.add_argument("--bastion-host", help="Bastion host IP address", default="192.168.16.26")
    parser.add_argument("--bastion-user", help="Bastion host SSH username", default="kang")

    args = parser.parse_args()

    # Set deployment configuration from arguments
    if args.deployment_user:
        os.environ["HOMELAB_USER"] = args.deployment_user

    if args.deployment_mode != "auto":
        os.environ["HOMELAB_DEPLOYMENT_MODE"] = args.deployment_mode

    if args.bastion_host:
        os.environ["HOMELAB_SERVER_IP"] = args.bastion_host

    if args.bastion_user:
        os.environ["HOMELAB_SSH_USER"] = args.bastion_user

    checker = RootlessCompatibilityChecker(args.kubeconfig, args.log_level)
    results = checker.run_comprehensive_compatibility_check()

    # Generate report
    report = checker.generate_compatibility_report(results)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)

    # Exit with error code if there are incompatibilities
    compatible_count = sum(1 for r in results if r.compatible)
    if compatible_count < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
