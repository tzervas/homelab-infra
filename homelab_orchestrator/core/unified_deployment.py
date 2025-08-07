"""Unified Deployment Manager - Centralized deployment functionality.

Replaces all bash deployment scripts with unified Python implementation.
"""

import asyncio
import logging
import shlex
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .config_manager import ConfigManager

@dataclass
class DeploymentCommand:
    """Structured deployment command."""
    program: str
    subcommand: str
    args: List[str]
    
    def to_list(self) -> List[str]:
        """Convert to argument list for subprocess."""
        return [self.program, self.subcommand, *self.args]
        
    @classmethod
    def from_string(cls, command: str) -> "DeploymentCommand":
        """Create from command string."""
        parts = shlex.split(command)
        if len(parts) < 2:
            msg = "Invalid command format"
            raise ValueError(msg)
        return cls(
            program=parts[0],
            subcommand=parts[1],
            args=parts[2:]
        )

@dataclass
class DeploymentStep:
    """Individual deployment step definition."""
    name: str
    description: str
    command: Optional[DeploymentCommand] = None
    function: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)
    timeout: int = 300
    critical: bool = True
    namespace: Optional[str] = None

@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    step_name: str
    status: str  # success, failure, warning, skipped
    duration: float
    output: str = ""
    error: str = ""
    recommendations: List[str] = field(default_factory=list)

class UnifiedDeploymentManager:
    """Unified deployment manager replacing all bash deployment scripts."""

    def __init__(self, config_manager: ConfigManager, project_root: Path) -> None:
        """Initialize the unified deployment manager."""
        self.config_manager = config_manager
        self.project_root = project_root
        self.logger = logging.getLogger(__name__)

        # Define allowed commands and subcommands for security
        self.ALLOWED_COMMANDS = {
            'kubectl': ['apply', 'delete', 'create'],
            'helm': ['repo', 'upgrade', 'install'],
        }

        # Deployment step registry
        self.deployment_steps = self._define_deployment_steps()
        self.completed_steps = set()
        self.failed_steps = set()

    def _validate_deployment_command(self, command: str) -> bool:
        """Validate a deployment command for security."""
        try:
            parts = shlex.split(command)
            if not parts:
                return False
                
            base_cmd = parts[0]
            if base_cmd not in self.ALLOWED_COMMANDS:
                return False
                
            # For kubectl/helm commands, validate subcommands
            if len(parts) > 1:
                subcmd = parts[1]
                if subcmd not in self.ALLOWED_COMMANDS[base_cmd]:
                    return False
                    
            # Validate file paths are under project root
            for part in parts:
                if part.startswith('-f'):
                    file_path = part[2:] or parts[parts.index(part) + 1]
                    full_path = (self.project_root / file_path).resolve()
                    if not str(full_path).startswith(str(self.project_root)):
                        return False
                        
            return True
            
        except Exception:
            return False

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
                # Validate command first
                cmd_str = " ".join(step.command.to_list())
                if not self._validate_deployment_command(cmd_str):
                    return DeploymentResult(
                        step_name=step.name,
                        status="failure",
                        duration=0.0,
                        error="Invalid command",
                        output="Command validation failed"
                    )

                # Execute command using subprocess_exec
                result = await asyncio.create_subprocess_exec(
                    step.command.program,
                    *step.command.to_list()[1:],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.project_root
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

    def _define_deployment_steps(self) -> dict[str, DeploymentStep]:
        """Define all deployment steps in correct order."""
        steps = {}
        
        def add_step(name: str, **kwargs) -> None:
            """Add a step with validation."""
            if "command" in kwargs:
                try:
                    cmd_str = kwargs["command"]
                    if not self._validate_deployment_command(cmd_str):
                        self.logger.error(f"Invalid command in step {name}")
                        return
                    kwargs["command"] = DeploymentCommand.from_string(cmd_str)
                except ValueError as e:
                    self.logger.error(f"Invalid command format in step {name}: {e}")
                    return
            steps[name] = DeploymentStep(name=name, **kwargs)
        
        # Define steps with validation
        add_step(
            "prerequisites",
            description="Validate deployment prerequisites",
            function=self._check_prerequisites,
            timeout=60,
        )
        add_step(
            "k3s_cluster",
            description="Deploy K3s Kubernetes cluster",
            function=self._deploy_k3s_cluster,
            dependencies=["prerequisites"],
            timeout=600,
        )
        add_step(
            "core_infrastructure",
            description="Deploy core infrastructure components",
            function=self._deploy_core_infrastructure,
            dependencies=["k3s_cluster"],
            timeout=300,
        )
        add_step(
            "metallb",
            description="Deploy MetalLB load balancer",
            command="kubectl apply -f kubernetes/base/metallb-config.yaml",
            dependencies=["core_infrastructure"],
            timeout=120,
        )
        add_step(
            "ingress_nginx",
            description="Deploy NGINX ingress controller",
            function=self._deploy_ingress_nginx,
            dependencies=["metallb"],
            timeout=180,
        )
        add_step(
            "cert_manager",
            description="Deploy cert-manager and cluster issuers",
            command="kubectl apply -f kubernetes/base/cluster-issuers.yaml",
            dependencies=["ingress_nginx"],
            timeout=120,
        )
        add_step(
            "keycloak",
            description="Deploy Keycloak authentication server",
            command="kubectl apply -f kubernetes/base/keycloak-deployment.yaml",
            dependencies=["cert_manager"],
            timeout=300,
            namespace="keycloak",
        )
        add_step(
            "oauth2_proxy",
            description="Deploy OAuth2 Proxy",
            command="kubectl apply -f kubernetes/base/oauth2-proxy.yaml",
            dependencies=["keycloak"],
            timeout=120,
            namespace="oauth2-proxy",
        )
        add_step(
            "monitoring",
            description="Deploy monitoring stack (Prometheus, Grafana)",
            function=self._deploy_monitoring,
            dependencies=["oauth2_proxy"],
            timeout=300,
            namespace="monitoring",
        )
        add_step(
            "gitlab",
            description="Deploy GitLab with Keycloak integration",
            command="kubectl apply -f kubernetes/base/gitlab-deployment.yaml",
            dependencies=["oauth2_proxy"],
            timeout=600,
            namespace="gitlab",
        )
        add_step(
            "ai_tools",
            description="Deploy AI tools (Ollama + OpenWebUI)",
            command="kubectl apply -f kubernetes/base/ollama-webui-deployment.yaml",
            dependencies=["oauth2_proxy"],
            timeout=300,
            namespace="ai-tools",
        )
        add_step(
            "jupyter",
            description="Deploy JupyterLab",
            command="kubectl apply -f kubernetes/base/jupyterlab-deployment.yaml",
            dependencies=["oauth2_proxy"],
            timeout=180,
            namespace="jupyter",
        )
        add_step(
            "landing_page",
            description="Deploy homelab landing page",
            command="kubectl apply -f kubernetes/base/landing-page.yaml",
            dependencies=["oauth2_proxy"],
            timeout=60,
            namespace="homelab-portal",
        )
        add_step(
            "gitlab_runner",
            description="Deploy GitLab Runner with ARC",
            command="kubectl apply -f kubernetes/base/gitlab-runner-arc.yaml",
            dependencies=["gitlab"],
            timeout=180,
            namespace="gitlab-runner",
            critical=False,
        )
        
        return steps

    async def _wait_for_namespace_ready(self, namespace: str, timeout: int = 300) -> bool:
        """Wait for all pods in namespace to be ready."""
        self.logger.info(f"Waiting for namespace {namespace} to be ready")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = await asyncio.create_subprocess_exec(
                    "kubectl",
                    "get",
                    "pods",
                    "-n",
                    namespace,
                    "--no-headers",
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

    async def deploy_full_infrastructure(
        self,
        components: Optional[List[str]] = None,
        skip_dependencies: bool = False,
        dry_run: bool = False,
    ) -> List[DeploymentResult]:
        """Deploy complete infrastructure or specific components."""
        self.logger.info("Starting unified infrastructure deployment")
        
        # Reset state for new deployment
        self.completed_steps.clear()
        self.failed_steps.clear()

        # Determine which steps to run
        if components:
            steps_to_run = self._resolve_dependencies(components, skip_dependencies)
        else:
            steps_to_run = list(self.deployment_steps.keys())

        # Deduplicate steps_to_run to prevent redundant execution when dependencies overlap
        steps_to_run = list(dict.fromkeys(steps_to_run))

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

    def _resolve_dependencies(self, components: List[str], skip_dependencies: bool) -> List[str]:
        """Resolve component dependencies and return ordered list."""
        if skip_dependencies:
            return components

        resolved = []
        visited = set()
        visiting = set()  # Track components currently being visited to detect cycles

        def resolve_component(component: str) -> None:
            if component in visited:
                return
            if component in visiting:
                msg = f"Dependency cycle detected involving component: {component}"
                raise ValueError(msg)
            
            visiting.add(component)

            if component in self.deployment_steps:
                step = self.deployment_steps[component]
                for dep in step.dependencies:
                    resolve_component(dep)
                resolved.append(component)
            
            visiting.remove(component)
            visited.add(component)

        for component in components:
            resolve_component(component)

        return resolved

    async def teardown_infrastructure(
        self,
        components: Optional[List[str]] = None,
        force: bool = False,
    ) -> List[DeploymentResult]:
        """Teardown infrastructure components."""
        self.logger.info("Starting infrastructure teardown")
        
        # Reset state for teardown operation
        self.completed_steps.clear()
        self.failed_steps.clear()

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
            cmd_args = []
            if step.namespace:
                # Delete namespace and all resources in it
                cmd_args = ["kubectl", "delete", "namespace", step.namespace, "--timeout=60s"]
            else:
                msg = f"Teardown not implemented for {step.name}"
                return DeploymentResult(
                    step_name=step.name,
                    status="warning",
                    duration=0.0,
                    output=msg,
                    error="Not implemented"
                )

            result = await asyncio.create_subprocess_exec(
                *cmd_args,
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

# Helper methods that implement specific deployment functionality
    async def _check_prerequisites(self) -> str:
        """Check deployment prerequisites."""
        checks = []

        # Check kubectl
        try:
            result = await asyncio.create_subprocess_exec(
                "kubectl",
                "version",
                "--client",
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

        # Execute K3s setup script - this is an exception to our normal rules
        # because it's a trusted script in our repo
        result = await asyncio.create_subprocess_exec(
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
        commands = [
            ["kubectl", "apply", "-f", "kubernetes/base/namespaces.yaml"],
            ["kubectl", "apply", "-f", "kubernetes/base/rbac.yaml"],
            ["kubectl", "apply", "-f", "kubernetes/base/network-policies.yaml"],
            ["kubectl", "apply", "-f", "kubernetes/base/security-contexts.yaml"],
        ]

        results = []
        for cmd_args in commands:
            result = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root,
            )
            stdout, stderr = await result.communicate()
            results.append(f"Command: {' '.join(cmd_args)}\nOutput: {stdout.decode()}")

        return "\n".join(results)

    async def _deploy_ingress_nginx(self) -> str:
        """Deploy NGINX ingress controller."""
        # Use Helm to deploy ingress-nginx
        commands = [
            ["helm", "repo", "add", "ingress-nginx", "https://kubernetes.github.io/ingress-nginx"],
            ["helm", "repo", "update"],
            ["helm", "upgrade", "--install", "ingress-nginx", "ingress-nginx/ingress-nginx",
             "--namespace", "ingress-nginx", "--create-namespace",
             "--set", "controller.service.type=LoadBalancer"],
        ]

        results = []
        for cmd_args in commands:
            result = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            results.append(f"Command: {' '.join(cmd_args)}\nOutput: {stdout.decode()}")

        return "\n".join(results)

    async def _deploy_monitoring(self) -> str:
        """Deploy monitoring stack."""
        commands = [
            ["kubectl", "apply", "-f", "kubernetes/base/prometheus-deployment.yaml"],
            ["kubectl", "apply", "-f", "kubernetes/base/grafana-deployment.yaml"],
        ]

        results = []
        for cmd_args in commands:
            result = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root,
            )
            stdout, stderr = await result.communicate()
            results.append(f"Command: {' '.join(cmd_args)}\nOutput: {stdout.decode()}")

        return "\n".join(results)
