"""
Unified Deployment Manager - Centralized deployment functionality.

Replaces all bash deployment scripts with unified Python implementation.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .config_manager import ConfigManager


@dataclass
class DeploymentStep:
    """Individual deployment step definition."""

    name: str
    description: str
    command: str | None = None
    function: Callable | None = None
    dependencies: list[str] = field(default_factory=list)
    timeout: int = 300
    critical: bool = True
    namespace: str | None = None


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""

    step_name: str
    status: str  # success, failure, warning, skipped
    duration: float
    output: str = ""
    error: str = ""
    recommendations: list[str] = field(default_factory=list)


class UnifiedDeploymentManager:
    """Unified deployment manager replacing all bash deployment scripts."""

    def __init__(self, config_manager: ConfigManager, project_root: Path) -> None:
        """Initialize the unified deployment manager."""
        self.config_manager = config_manager
        self.project_root = project_root
        self.logger = logging.getLogger(__name__)

        # Deployment step registry
        self.deployment_steps = self._define_deployment_steps()
        self.completed_steps = set()
        self.failed_steps = set()

    def _define_deployment_steps(self) -> dict[str, DeploymentStep]:
        """Define all deployment steps in correct order."""
        return {
            # Infrastructure prerequisites
            "prerequisites": DeploymentStep(
                name="prerequisites",
                description="Validate deployment prerequisites",
                function=self._check_prerequisites,
                timeout=60,
            ),
            # Core Kubernetes infrastructure
            "k3s_cluster": DeploymentStep(
                name="k3s_cluster",
                description="Deploy K3s Kubernetes cluster",
                function=self._deploy_k3s_cluster,
                dependencies=["prerequisites"],
                timeout=600,
            ),
            "core_infrastructure": DeploymentStep(
                name="core_infrastructure",
                description="Deploy core infrastructure components",
                function=self._deploy_core_infrastructure,
                dependencies=["k3s_cluster"],
                timeout=300,
            ),
            "metallb": DeploymentStep(
                name="metallb",
                description="Deploy MetalLB load balancer",
                command="kubectl apply -f kubernetes/base/metallb-config.yaml",
                dependencies=["core_infrastructure"],
                timeout=120,
            ),
            "ingress_nginx": DeploymentStep(
                name="ingress_nginx",
                description="Deploy NGINX ingress controller",
                function=self._deploy_ingress_nginx,
                dependencies=["metallb"],
                timeout=180,
            ),
            "cert_manager": DeploymentStep(
                name="cert_manager",
                description="Deploy cert-manager and cluster issuers",
                command="kubectl apply -f kubernetes/base/cluster-issuers.yaml",
                dependencies=["ingress_nginx"],
                timeout=120,
            ),
            # Authentication infrastructure
            "keycloak": DeploymentStep(
                name="keycloak",
                description="Deploy Keycloak authentication server",
                command="kubectl apply -f kubernetes/base/keycloak-deployment.yaml",
                dependencies=["cert_manager"],
                timeout=300,
                namespace="keycloak",
            ),
            "oauth2_proxy": DeploymentStep(
                name="oauth2_proxy",
                description="Deploy OAuth2 Proxy",
                command="kubectl apply -f kubernetes/base/oauth2-proxy.yaml",
                dependencies=["keycloak"],
                timeout=120,
                namespace="oauth2-proxy",
            ),
            # Application services
            "monitoring": DeploymentStep(
                name="monitoring",
                description="Deploy monitoring stack (Prometheus, Grafana)",
                function=self._deploy_monitoring,
                dependencies=["oauth2_proxy"],
                timeout=300,
                namespace="monitoring",
            ),
            "gitlab": DeploymentStep(
                name="gitlab",
                description="Deploy GitLab with Keycloak integration",
                command="kubectl apply -f kubernetes/base/gitlab-deployment.yaml",
                dependencies=["oauth2_proxy"],
                timeout=600,
                namespace="gitlab",
            ),
            "ai_tools": DeploymentStep(
                name="ai_tools",
                description="Deploy AI tools (Ollama + OpenWebUI)",
                command="kubectl apply -f kubernetes/base/ollama-webui-deployment.yaml",
                dependencies=["oauth2_proxy"],
                timeout=300,
                namespace="ai-tools",
            ),
            "jupyter": DeploymentStep(
                name="jupyter",
                description="Deploy JupyterLab",
                command="kubectl apply -f kubernetes/base/jupyterlab-deployment.yaml",
                dependencies=["oauth2_proxy"],
                timeout=180,
                namespace="jupyter",
            ),
            "landing_page": DeploymentStep(
                name="landing_page",
                description="Deploy homelab landing page",
                command="kubectl apply -f kubernetes/base/landing-page.yaml",
                dependencies=["oauth2_proxy"],
                timeout=60,
                namespace="homelab-portal",
            ),
            # Optional components
            "gitlab_runner": DeploymentStep(
                name="gitlab_runner",
                description="Deploy GitLab Runner with ARC",
                command="kubectl apply -f kubernetes/base/gitlab-runner-arc.yaml",
                dependencies=["gitlab"],
                timeout=180,
                namespace="gitlab-runner",
                critical=False,
            ),
        }

    async def deploy_full_infrastructure(
        self,
        components: list[str] | None = None,
        skip_dependencies: bool = False,
        dry_run: bool = False,
    ) -> list[DeploymentResult]:
        """Deploy complete infrastructure or specific components."""
        self.logger.info("Starting unified infrastructure deployment")

        # Determine which steps to run
        if components:
            steps_to_run = self._resolve_dependencies(components, skip_dependencies)
        else:
            steps_to_run = list(self.deployment_steps.keys())

        results = []

        for step_name in steps_to_run:
            step = self.deployment_steps[step_name]

            # Check dependencies
            if not skip_dependencies:
                missing_deps = [dep for dep in step.dependencies if dep not in self.completed_steps]
                if missing_deps:
                    self.logger.warning(
                        f"Skipping {step_name}: missing dependencies {missing_deps}",
                    )
                    continue

            # Execute step
            result = await self._execute_step(step, dry_run)
            results.append(result)

            # Track completion
            if result.status == "success":
                self.completed_steps.add(step_name)
            elif result.status == "failure" and step.critical:
                self.failed_steps.add(step_name)
                self.logger.error(f"Critical step {step_name} failed, stopping deployment")
                break
            elif result.status == "failure":
                self.failed_steps.add(step_name)
                self.logger.warning(f"Non-critical step {step_name} failed, continuing")

        return results

    async def _execute_step(self, step: DeploymentStep, dry_run: bool) -> DeploymentResult:
        """Execute a single deployment step."""
        start_time = time.time()
        self.logger.info(f"Executing step: {step.name}")

        if dry_run:
            return DeploymentResult(
                step_name=step.name,
                status="success",
                duration=0.1,
                output="Dry run - step skipped",
            )

        try:
            if step.function:
                # Execute Python function
                output = await step.function()
                status = "success"
                error = ""
            elif step.command:
                # Execute shell command
                result = await asyncio.create_subprocess_shell(
                    step.command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.project_root,
                )

                stdout, stderr = await asyncio.wait_for(
                    result.communicate(),
                    timeout=step.timeout,
                )

                output = stdout.decode()
                error = stderr.decode()
                status = "success" if result.returncode == 0 else "failure"
            else:
                output = f"No execution method defined for step {step.name}"
                status = "failure"
                error = "Configuration error"

            # Wait for resources to be ready if namespace specified
            if step.namespace and status == "success":
                await self._wait_for_namespace_ready(step.namespace)

        except asyncio.TimeoutError:
            output = f"Step {step.name} timed out after {step.timeout}s"
            status = "failure"
            error = "Timeout"
        except Exception as e:
            output = f"Step {step.name} failed with exception"
            status = "failure"
            error = str(e)

        duration = time.time() - start_time

        return DeploymentResult(
            step_name=step.name,
            status=status,
            duration=duration,
            output=output,
            error=error,
        )

    async def _check_prerequisites(self) -> str:
        """Check deployment prerequisites."""
        checks = []

        # Check kubectl
        try:
            result = await asyncio.create_subprocess_shell(
                "kubectl version --client",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.communicate()
            checks.append("✅ kubectl available")
        except Exception:
            checks.append("❌ kubectl not available")

        # Check required files
        required_files = [
            "kubernetes/base/keycloak-deployment.yaml",
            "kubernetes/base/oauth2-proxy.yaml",
            "kubernetes/base/gitlab-deployment.yaml",
            "kubernetes/base/grafana-deployment.yaml",
        ]

        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                checks.append(f"✅ {file_path} exists")
            else:
                checks.append(f"❌ {file_path} missing")

        return "\n".join(checks)

    async def _deploy_k3s_cluster(self) -> str:
        """Deploy K3s cluster using existing script."""
        script_path = self.project_root / "clean-and-setup-k3s.sh"
        if not script_path.exists():
            msg = "K3s setup script not found"
            raise FileNotFoundError(msg)

        # Execute K3s setup script
        result = await asyncio.create_subprocess_shell(
            str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await result.communicate()

        if result.returncode != 0:
            msg = f"K3s setup failed: {stderr.decode()}"
            raise RuntimeError(msg)

        return stdout.decode()

    async def _deploy_core_infrastructure(self) -> str:
        """Deploy core infrastructure components."""
        components = [
            "kubectl apply -f kubernetes/base/namespaces.yaml",
            "kubectl apply -f kubernetes/base/rbac.yaml",
            "kubectl apply -f kubernetes/base/network-policies.yaml",
            "kubectl apply -f kubernetes/base/security-contexts.yaml",
        ]

        results = []
        for command in components:
            result = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root,
            )
            stdout, stderr = await result.communicate()
            results.append(f"Command: {command}\nOutput: {stdout.decode()}")

        return "\n".join(results)

    async def _deploy_ingress_nginx(self) -> str:
        """Deploy NGINX ingress controller."""
        # Use Helm to deploy ingress-nginx
        commands = [
            "helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx",
            "helm repo update",
            "helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --create-namespace --set controller.service.type=LoadBalancer",
        ]

        results = []
        for command in commands:
            result = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            results.append(f"Command: {command}\nOutput: {stdout.decode()}")

        return "\n".join(results)

    async def _deploy_monitoring(self) -> str:
        """Deploy monitoring stack."""
        # Apply monitoring manifests
        commands = [
            "kubectl apply -f kubernetes/base/prometheus-deployment.yaml",
            "kubectl apply -f kubernetes/base/grafana-deployment.yaml",
        ]

        results = []
        for command in commands:
            result = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root,
            )
            stdout, stderr = await result.communicate()
            results.append(f"Command: {command}\nOutput: {stdout.decode()}")

        return "\n".join(results)

    async def _wait_for_namespace_ready(self, namespace: str, timeout: int = 300) -> bool:
        """Wait for all pods in namespace to be ready."""
        self.logger.info(f"Waiting for namespace {namespace} to be ready")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = await asyncio.create_subprocess_shell(
                    f"kubectl get pods -n {namespace} --no-headers",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await result.communicate()

                if result.returncode == 0:
                    lines = stdout.decode().strip().split("\n")
                    if not lines or lines == [""]:
                        # No pods yet, continue waiting
                        await asyncio.sleep(5)
                        continue

                    all_ready = True
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 2:
                            ready_status = parts[1]
                            pod_status = parts[2]

                            if pod_status not in ["Running", "Completed"]:
                                all_ready = False
                                break

                            if "/" in ready_status:
                                ready, total = ready_status.split("/")
                                if ready != total:
                                    all_ready = False
                                    break

                    if all_ready:
                        self.logger.info(f"Namespace {namespace} is ready")
                        return True

                await asyncio.sleep(10)

            except Exception as e:
                self.logger.warning(f"Error checking namespace {namespace}: {e}")
                await asyncio.sleep(10)

        self.logger.warning(f"Timeout waiting for namespace {namespace}")
        return False

    def _resolve_dependencies(self, components: list[str], skip_dependencies: bool) -> list[str]:
        """Resolve component dependencies and return ordered list."""
        if skip_dependencies:
            return components

        resolved = []
        visited = set()

        def resolve_component(component: str) -> None:
            if component in visited:
                return
            visited.add(component)

            if component in self.deployment_steps:
                step = self.deployment_steps[component]
                for dep in step.dependencies:
                    resolve_component(dep)
                resolved.append(component)

        for component in components:
            resolve_component(component)

        return resolved

    async def teardown_infrastructure(
        self,
        components: list[str] | None = None,
        force: bool = False,
    ) -> list[DeploymentResult]:
        """Teardown infrastructure components."""
        self.logger.info("Starting infrastructure teardown")

        if components:
            steps_to_teardown = components
        else:
            # Reverse order for teardown
            steps_to_teardown = list(reversed(list(self.deployment_steps.keys())))

        results = []

        for step_name in steps_to_teardown:
            if step_name not in self.deployment_steps:
                continue

            step = self.deployment_steps[step_name]
            result = await self._teardown_step(step, force)
            results.append(result)

        return results

    async def _teardown_step(self, step: DeploymentStep, force: bool) -> DeploymentResult:
        """Teardown a single deployment step."""
        start_time = time.time()
        self.logger.info(f"Tearing down step: {step.name}")

        try:
            if step.namespace:
                # Delete namespace and all resources in it
                command = f"kubectl delete namespace {step.namespace} --timeout=60s"
            else:
                # For core components, use specific teardown logic
                command = f"echo 'Teardown not implemented for {step.name}'"

            result = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await result.communicate()

            status = "success" if result.returncode == 0 else "warning"
            output = stdout.decode()
            error = stderr.decode()

        except Exception as e:
            status = "failure"
            output = f"Teardown failed for {step.name}"
            error = str(e)

        duration = time.time() - start_time

        return DeploymentResult(
            step_name=step.name,
            status=status,
            duration=duration,
            output=output,
            error=error,
        )
