# Homelab Infrastructure

Infrastructure as Code (IaC) for managing homelab k3s environment with Helm and GitOps principles.

## Overview

This repository contains the complete infrastructure configuration for a homelab environment, featuring:

- **k3s** - Lightweight Kubernetes distribution
- **Terraform** - Infrastructure provisioning
- **Helm/Helmfile** - Declarative application deployment
- **MetalLB** - Bare metal load balancer
- **Longhorn** - Distributed block storage
- **Prometheus Stack** - Comprehensive monitoring
- **Cert-Manager** - Automatic TLS certificate management
- **Ingress-Nginx** - Ingress controller

## Quick Start

### Prerequisites

- A homelab server with SSH access
- kubectl configured
- Helm 3.x installed
- Ansible installed
- At least 16GB RAM and 200GB disk space

### Configuration Setup

This project uses a multi-repository approach for security:

1. **Main Repository** (this one): Public infrastructure code and documentation
2. **Private Repository**: Sensitive configurations, secrets, and environment overrides
3. **Examples Repository**: Template configurations

#### Setting up Private Configuration

1. Create a private repository for your sensitive configurations:
   ```bash
   # Example: Create a private repo on GitHub/GitLab
   git clone git@github.com:username/homelab-infra-private.git
   ```

2. Configure the private repository in your `.env` file:
   ```bash
   PRIVATE_CONFIG_REPO=git@github.com:username/homelab-infra-private.git
   PRIVATE_CONFIG_BRANCH=main
   PRIVATE_CONFIG_DIR=config
   ```

3. Initialize the private configuration:
   ```bash
   ./scripts/sync-private-config.sh sync
   ```

This will automatically clone your private repo, set up the directory structure, and load sensitive environment variables during deployment.

### Configuration Setup

This project uses a multi-repository approach for security:

1. **Main Repository** (this one): Public infrastructure code and documentation
2. **Private Repository**: Sensitive configurations, secrets, and environment overrides
3. **Examples Repository**: Template configurations

#### Setting up Private Configuration

1. Create a private repository for your sensitive configurations:
   ```bash
   # Example: Create a private repo on GitHub/GitLab
   git clone git@github.com:username/homelab-infra-private.git
   ```

2. Configure the private repository in your `.env` file:
   ```bash
   PRIVATE_CONFIG_REPO=git@github.com:username/homelab-infra-private.git
   PRIVATE_CONFIG_BRANCH=main
   PRIVATE_CONFIG_DIR=config
   ```

3. Initialize the private configuration:
   ```bash
   ./scripts/sync-private-config.sh sync
   ```

This will automatically clone your private repo, set up the directory structure, and load sensitive environment variables during deployment.

### Deploy Infrastructure

```bash
# Clone the repository
git clone <your-repo-url>
cd homelab-infra

# Deploy development environment
./scripts/deploy.sh -e development

# Deploy production environment
./scripts/deploy.sh -e production
```

## Private Documentation

This repository includes public documentation in the `docs/` directory. Detailed architecture, network configuration, and other sensitive documentation is maintained locally in the `.private/docs/` directory, which is not tracked in git. These private documents are synchronized across branches using the local backup scripts.

## Repository Structure

```
.
├── .gitignore         # Git ignore patterns
├── LICENSE           # MIT License
├── README.md         # This documentation
├── docs/            # Additional documentation
│   ├── k3s-setup.md        # k3s installation guide
│   └── claude_integration.md
├── helm/                    # Helm configurations
│   ├── charts/             # Custom Helm charts
│   │   ├── core-infrastructure/  # MetalLB, cert-manager, ingress
│   │   ├── monitoring/     # Prometheus, Grafana, Loki
│   │   └── storage/        # Longhorn storage
│   ├── environments/       # Environment-specific values
│   ├── repositories.yaml   # Helm repository definitions
│   └── helmfile.yaml      # Declarative release management
├── kubernetes/             # Base Kubernetes manifests
│   ├── base/              # Namespace, RBAC, network policies
│   └── overlays/          # Environment-specific overlays
├── scripts/               # Deployment and utility scripts
└── terraform/            # Terraform configurations
    ├── main.tf            # Main Terraform configuration
    ├── variables.tf       # Input variables
    └── outputs.tf         # Output variables
```

## Getting Started

Documentation for setup and usage can be found in the [docs](./docs) directory.

## Network Configuration

### Server Details (customize in your private config)
- **k3s Master**: Your homelab server IP
- **Network Range**: Your internal network range

### MetalLB IP Allocation (customize in your private config)
- **Development**: A small IP range for testing
- **Staging**: Medium IP range for staging
- **Production**: Larger IP range for production

## Environments

### Development
- Reduced resource allocation
- Single replica deployment
- Basic monitoring
- Self-signed certificates

### Staging
- Production-like configuration
- Full monitoring stack
- Let's Encrypt staging certificates
- 2 replica deployment

### Production
- Full resource allocation
- High availability where possible
- Let's Encrypt production certificates
- 3 replica deployment for storage

## Key Components

### Core Infrastructure
- **MetalLB**: Load balancer for bare metal
- **cert-manager**: Automatic TLS certificates
- **ingress-nginx**: HTTP/HTTPS ingress
- **sealed-secrets**: Encrypted secret management

### Storage
- **Longhorn**: Distributed block storage with snapshots and backups
- **Local-path**: Fast local storage for non-critical data

### Monitoring
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **Loki**: Log aggregation
- **Promtail**: Log collection agent

## Deployment Commands

```bash
# Deploy specific environment
./scripts/deploy.sh -e production

# Dry run deployment
./scripts/deploy.sh -e production --dry-run

# Skip dependency updates
./scripts/deploy.sh -e development --skip-deps

# Update only specific release
helmfile --environment production apply --selector name=prometheus
```

## Access URLs

After deployment, services will be available at:

### Development
- Grafana: https://grafana.dev.homelab.local
- Longhorn: https://longhorn.dev.homelab.local
- Prometheus: https://prometheus.dev.homelab.local

### Production
- Grafana: https://grafana.homelab.local
- Longhorn: https://longhorn.homelab.local
- Prometheus: https://prometheus.homelab.local

## Security

### Authentication
- Basic authentication for Longhorn UI
- Grafana admin credentials in values files
- Sealed secrets for production credentials

### Network Policies
- Default deny-all policies
- Selective ingress/egress rules
- Namespace isolation

### Pod Security
- Pod Security Standards enforced
- Privileged access only where required
- Resource limits on all workloads

## Monitoring

### Metrics
- Node and pod metrics via node-exporter
- Application metrics via ServiceMonitor CRDs
- Custom dashboards in Grafana

### Logging
- Centralized logging with Loki
- Log retention policies
- Grafana integration for log exploration

### Alerting
- Prometheus AlertManager
- Critical system alerts
- Slack/email notification support (configure in values)

## Backup Strategy

### Longhorn Backups
- Configure S3/NFS backup targets in production values
- Automated snapshot schedules
- Cross-cluster disaster recovery

### Configuration Backups
- Git-based infrastructure as code
- Sealed secrets for sensitive data
- Regular cluster state exports

## Troubleshooting

### Common Issues

1. **MetalLB not assigning IPs**
   ```bash
   kubectl logs -n metallb-system -l app=metallb
   kubectl get ipaddresspool -n metallb-system
   ```

2. **Cert-manager certificate issues**
   ```bash
   kubectl describe certificate -A
   kubectl logs -n cert-manager -l app=cert-manager
   ```

3. **Longhorn storage issues**
   ```bash
   kubectl get volumes -n longhorn-system
   kubectl logs -n longhorn-system -l app=longhorn-manager
   ```

### Log Collection
```bash
# Collect all infrastructure logs
kubectl logs -n metallb-system -l app=metallb > metallb.log
kubectl logs -n cert-manager -l app=cert-manager > cert-manager.log
kubectl logs -n longhorn-system -l app=longhorn-manager > longhorn.log
```

## Contributing

1. Create a feature branch from `develop` using:
   ```bash
   git checkout -b feature/your-feature-name develop
   ```
2. Make your changes
3. Test changes in development environment
4. Update documentation as needed
5. Submit a pull request to `develop`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
