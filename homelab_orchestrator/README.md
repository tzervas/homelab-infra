# Homelab Orchestrator

A comprehensive Python-based orchestration framework for managing homelab infrastructure deployments, configurations, and operations.

## Overview

The Homelab Orchestrator provides a unified interface for managing complex homelab infrastructure across multiple technologies including Kubernetes, Helm, Terraform, and Ansible. It serves as the central control plane for deployment automation, configuration management, and operational tasks.

## Architecture

```
homelab_orchestrator/
├── cli.py                  # Command-line interface
├── __main__.py            # Entry point for module execution
├── core/                  # Core orchestration components
│   ├── config_manager.py  # Configuration management
│   ├── deployment.py      # Deployment orchestration
│   ├── gpu_manager.py     # GPU resource management
│   ├── health.py          # Health monitoring
│   ├── orchestrator.py    # Main orchestration engine
│   ├── security.py        # Security management
│   └── unified_deployment.py # Unified deployment workflows
├── portal/                # Web portal interface
│   ├── main.py           # Portal application entry
│   ├── portal_manager.py # Portal management logic
│   ├── api/              # REST API endpoints
│   ├── models/           # Data models
│   ├── services/         # Business logic services
│   ├── static/           # Static web assets
│   └── templates/        # HTML templates
├── remote/               # Remote cluster management
│   └── cluster_manager.py # Remote cluster operations
├── security/             # Security components
│   └── privilege_manager.py # Privilege management
├── validation/           # Validation framework
│   └── validator.py      # Configuration validators
├── webhooks/             # Webhook management
│   └── manager.py        # Webhook processing
└── tests/                # Test suite
    └── test_cli.py       # CLI tests
```

## Features

### Core Orchestration

- **Unified Deployment**: Single interface for deploying across Helm, Kubernetes, Terraform
- **Configuration Management**: Centralized configuration with environment-specific overrides
- **Health Monitoring**: Continuous health checks and alerting
- **Security Management**: Integrated security policies and privilege management

### Web Portal

- **Dashboard Interface**: Web-based management console
- **Real-time Monitoring**: Live status updates and metrics
- **Configuration Editor**: GUI for editing configurations
- **Deployment Tracking**: Visual deployment progress and history

### Remote Management

- **Multi-Cluster Support**: Manage multiple Kubernetes clusters
- **Remote Execution**: Execute commands on remote infrastructure
- **Centralized Monitoring**: Aggregate monitoring across clusters

### Security Features

- **Privilege Management**: Fine-grained access control
- **Security Validation**: Automated security policy compliance
- **Audit Logging**: Comprehensive audit trails

## Installation

### Prerequisites

- Python 3.11+
- Kubernetes cluster access
- Helm 3.x
- Terraform (optional)

### Install from Source

```bash
# Clone repository
git clone <repository-url>
cd homelab-infra

# Install orchestrator
pip install -e ./homelab_orchestrator

# Or install with development dependencies
pip install -e "./homelab_orchestrator[dev]"
```

## Usage

### Command Line Interface

```bash
# Basic deployment
homelab-orchestrator deploy --environment development

# Health check
homelab-orchestrator health --cluster homelab

# Configuration validation
homelab-orchestrator validate --config config/consolidated/

# Portal management
homelab-orchestrator portal start --port 8080
```

### Python Module

```python
from homelab_orchestrator.core import orchestrator
from homelab_orchestrator.core.config_manager import ConfigManager

# Initialize orchestrator
config = ConfigManager('config/consolidated/')
orch = orchestrator.Orchestrator(config)

# Deploy infrastructure
result = orch.deploy_infrastructure('development')

# Health monitoring
health_status = orch.check_health()
```

### Web Portal

```bash
# Start the web portal
homelab-orchestrator portal start

# Access at http://localhost:8080
# Default credentials: admin / see configuration
```

## Configuration

### Environment Configuration

Configure environments in `config/consolidated/environments.yaml`:

```yaml
environments:
  development:
    cluster:
      name: "dev-cluster"
      kubeconfig: "~/.kube/config"
    resources:
      limits:
        cpu: "2"
        memory: "4Gi"

  production:
    cluster:
      name: "prod-cluster"
      kubeconfig: "/etc/kubernetes/prod-config"
    resources:
      limits:
        cpu: "8"
        memory: "16Gi"
```

### Security Configuration

Security policies in `config/consolidated/security.yaml`:

```yaml
security:
  rbac:
    enabled: true
    default_permissions: "read"

  network_policies:
    enabled: true
    default_deny: true

  pod_security:
    enforce: "restricted"
    audit: "restricted"
    warn: "restricted"
```

## API Reference

### Core Classes

#### Orchestrator

Main orchestration engine for managing deployments.

```python
class Orchestrator:
    def __init__(self, config_manager: ConfigManager)
    def deploy_infrastructure(self, environment: str) -> DeploymentResult
    def check_health(self) -> HealthStatus
    def validate_configuration(self) -> ValidationResult
```

#### ConfigManager

Centralized configuration management.

```python
class ConfigManager:
    def __init__(self, config_path: str)
    def get_environment_config(self, env: str) -> dict
    def validate_config(self) -> bool
    def reload_config(self) -> None
```

#### DeploymentManager

Handles deployment orchestration across multiple tools.

```python
class DeploymentManager:
    def deploy_helm_charts(self, charts: list) -> DeploymentResult
    def apply_kubernetes_manifests(self, manifests: list) -> DeploymentResult
    def execute_terraform(self, module_path: str) -> DeploymentResult
```

### CLI Commands

| Command | Description | Options |
|---------|-------------|---------|
| `deploy` | Deploy infrastructure | `--environment`, `--dry-run`, `--parallel` |
| `health` | Check system health | `--cluster`, `--detailed`, `--format` |
| `validate` | Validate configurations | `--config`, `--environment`, `--strict` |
| `portal` | Manage web portal | `start`, `stop`, `status`, `--port` |
| `config` | Configuration management | `show`, `validate`, `reload` |

## Development

### Setting up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=homelab_orchestrator

# Run specific test categories
pytest -k "test_deployment"
pytest -k "test_security"
```

### Code Style

The project uses:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

```bash
# Format code
black homelab_orchestrator/
isort homelab_orchestrator/

# Check linting
flake8 homelab_orchestrator/
mypy homelab_orchestrator/
```

## Integration

### Helm Integration

- Automatic chart dependency management
- Values file templating and validation
- Release lifecycle management

### Kubernetes Integration

- Manifest validation and application
- Resource monitoring and status tracking
- Custom resource definitions support

### Terraform Integration

- Module execution and state management
- Variable injection from configuration
- Plan validation and approval workflows

### Ansible Integration

- Playbook execution for system setup
- Inventory management from configuration
- Variable synchronization

## Monitoring and Observability

### Health Monitoring

- Cluster health checks
- Application readiness probes
- Resource utilization monitoring

### Logging

- Structured logging with JSON output
- Log aggregation and forwarding
- Audit trail maintenance

### Metrics

- Deployment success/failure rates
- Performance metrics collection
- Custom metrics via portal

## Security

### Authentication

- OIDC/OAuth2 integration
- Service account management
- API key authentication

### Authorization

- Role-based access control (RBAC)
- Fine-grained permissions
- Resource-level access control

### Security Scanning

- Configuration security validation
- Vulnerability scanning integration
- Policy compliance checking

## Troubleshooting

### Common Issues

#### Configuration Validation Failures

```bash
# Validate specific configuration
homelab-orchestrator validate --config config/consolidated/domains.yaml

# Check configuration syntax
homelab-orchestrator config validate --strict
```

#### Deployment Failures

```bash
# Check deployment status
homelab-orchestrator health --detailed

# View deployment logs
homelab-orchestrator logs --deployment <deployment-name>

# Rollback deployment
homelab-orchestrator rollback --deployment <deployment-name>
```

#### Portal Access Issues

```bash
# Check portal status
homelab-orchestrator portal status

# Restart portal
homelab-orchestrator portal restart

# Check portal logs
homelab-orchestrator portal logs
```

### Debug Mode

Enable debug logging:

```bash
export HOMELAB_LOG_LEVEL=DEBUG
homelab-orchestrator --debug deploy --environment development
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes and add tests
4. Ensure all tests pass (`pytest`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Contribution Guidelines

- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed
- Ensure all CI checks pass

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## Support

- **Documentation**: [docs/](../docs/)
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

## Related Projects

- [Helm Charts](../helm/) - Helm chart definitions
- [Kubernetes Manifests](../kubernetes/) - Raw Kubernetes resources
- [Terraform Modules](../terraform/) - Infrastructure as code
- [Ansible Playbooks](../ansible/) - System configuration
