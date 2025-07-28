# Terraform Integration Architecture

**Version:** 2.0  
**Date:** December 2024  
**Author:** Infrastructure Team  

## Overview

This document details the comprehensive Terraform integration patterns and usage for the modernized homelab infrastructure. Terraform serves as the Infrastructure as Code (IaC) foundation, managing infrastructure provisioning, networking, security, and storage components.

## Architecture Principles

### Infrastructure as Code

- **Declarative Configuration**: All infrastructure defined as code
- **Version Control**: Infrastructure changes tracked in Git
- **Repeatability**: Consistent deployments across environments
- **Collaboration**: Team-based infrastructure management

### State Management

- **Remote State**: Centralized state storage for team collaboration
- **State Locking**: Prevents concurrent modifications
- **Backup and Recovery**: Automated state backup procedures
- **Drift Detection**: Automated detection and remediation

## Directory Structure

```
terraform/
├── main.tf                     # Root configuration
├── variables.tf                # Global variables
├── outputs.tf                  # Global outputs
├── terraform.tfvars.example    # Example variables
├── modules/                    # Reusable modules
│   ├── k3s-cluster/           # K3s cluster management
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── scripts/           # Installation scripts
│   │   └── templates/         # Configuration templates
│   ├── networking/            # Network infrastructure
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── templates/         # Network configs
│   ├── security/              # Security components
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── storage/               # Storage provisioning
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── environments/              # Environment-specific configs
│   ├── development/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   └── production/
└── providers/                 # Custom providers
    ├── homelab.tf
    └── README.md
```

## Module Architecture

### K3s Cluster Module

**Purpose**: Manages K3s cluster lifecycle, configuration, and nodes

#### Features

- **Automated Installation**: K3s installation with custom configurations
- **Node Management**: Master and worker node provisioning
- **Network Configuration**: Cluster networking and CIDR management
- **Security Hardening**: Rootless mode and security policies
- **Component Management**: Enable/disable built-in components

#### Usage

```hcl
module "k3s_cluster" {
  source = "./modules/k3s-cluster"
  
  # Cluster Configuration
  cluster_name    = "homelab-k3s"
  cluster_domain  = "cluster.local"
  cluster_cidr    = "10.42.0.0/16"
  service_cidr    = "10.43.0.0/16"
  
  # Node Configuration
  master_nodes = [
    {
      name = "master-1"
      ip   = "192.168.16.26"
      role = "server"
    }
  ]
  
  worker_nodes = [
    {
      name = "worker-1"
      ip   = "192.168.16.27"
      role = "agent"
    }
  ]
  
  # Security Configuration
  enable_rootless     = true
  disable_traefik     = true
  disable_servicelb   = true
  
  # Custom Configuration
  extra_server_args = [
    "--disable=metrics-server",
    "--kube-controller-manager-arg=terminated-pod-gc-threshold=10"
  ]
  
  tags = {
    Environment = var.environment
    Terraform   = "true"
  }
}
```

#### Outputs

```hcl
output "kubeconfig" {
  description = "Kubernetes configuration file content"
  value       = module.k3s_cluster.kubeconfig
  sensitive   = true
}

output "cluster_endpoint" {
  description = "Kubernetes API server endpoint"
  value       = module.k3s_cluster.cluster_endpoint
}

output "cluster_ca_certificate" {
  description = "Cluster CA certificate"
  value       = module.k3s_cluster.cluster_ca_certificate
  sensitive   = true
}
```

### Networking Module

**Purpose**: Manages network infrastructure, load balancing, and ingress

#### Features

- **MetalLB Management**: Load balancer IP pool configuration
- **Ingress Controller**: NGINX ingress with SSL termination
- **DNS Configuration**: CoreDNS customization
- **Network Policies**: Security policy templates
- **Service Mesh**: Istio/Linkerd integration support

#### Usage

```hcl
module "networking" {
  source = "./modules/networking"
  
  # MetalLB Configuration
  enable_metallb = true
  metallb_ip_pools = {
    development = {
      name      = "dev-pool"
      addresses = ["192.168.25.200-192.168.25.210"]
    }
    production = {
      name      = "prod-pool"
      addresses = ["192.168.25.240-192.168.25.250"]
    }
  }
  
  # Ingress Configuration
  enable_ingress_nginx = true
  ingress_class        = "nginx"
  enable_ssl_passthrough = true
  
  # DNS Configuration
  enable_custom_dns = true
  dns_entries = {
    "homelab.local" = "192.168.25.240"
    "*.apps.homelab.local" = "192.168.25.241"
  }
  
  # Network Policies
  enable_network_policies = true
  default_deny_all       = true
  
  environment = var.environment
}
```

#### Advanced Networking Features

```hcl
# Service Mesh Integration
module "networking" {
  # ... base configuration ...
  
  # Istio Service Mesh
  enable_istio = true
  istio_config = {
    version           = "1.19.0"
    enable_mtls       = true
    enable_tracing    = true
    enable_telemetry  = true
  }
  
  # VLAN Support with Multus
  enable_multus = true
  vlan_configs = [
    {
      name    = "vlan-100"
      vlan_id = 100
      subnet  = "10.100.0.0/24"
    }
  ]
}
```

### Security Module

**Purpose**: Manages security infrastructure and policies

#### Features

- **Certificate Management**: cert-manager with multiple issuers
- **Secret Management**: External Secrets Operator integration
- **RBAC Configuration**: Role-based access control
- **Security Policies**: Pod Security Standards and policies
- **Runtime Security**: Falco integration

#### Usage

```hcl
module "security" {
  source = "./modules/security"
  
  # Certificate Management
  enable_cert_manager = true
  cert_manager_config = {
    version = "v1.13.0"
    enable_webhook = true
    enable_acme    = true
  }
  
  # Let's Encrypt Configuration
  enable_letsencrypt = true
  letsencrypt_config = {
    email  = "tz-dev@vectorweight.com"
    server = "https://acme-v02.api.letsencrypt.org/directory"
    staging_server = "https://acme-staging-v02.api.letsencrypt.org/directory"
  }
  
  # External Secrets
  enable_external_secrets = true
  external_secrets_config = {
    version = "0.9.0"
    backends = ["kubernetes", "vault"]
  }
  
  # Security Policies
  enable_pod_security_standards = true
  pod_security_config = {
    enforce = "restricted"
    audit   = "restricted"
    warn    = "restricted"
  }
  
  # RBAC Configuration
  rbac_roles = [
    {
      name = "developer"
      rules = [
        {
          api_groups = [""]
          resources  = ["pods", "services"]
          verbs      = ["get", "list", "create", "update", "delete"]
        }
      ]
    }
  ]
  
  environment = var.environment
}
```

#### Advanced Security Features

```hcl
# Runtime Security with Falco
module "security" {
  # ... base configuration ...
  
  enable_falco = true
  falco_config = {
    version = "0.36.0"
    rules = [
      "falco_rules.yaml",
      "k8s_audit_rules.yaml",
      "application_rules.yaml"
    ]
    outputs = {
      rate        = 1
      max_burst   = 1000
      syslog      = true
      json_output = true
    }
  }
  
  # Network Security
  enable_network_policies = true
  network_policy_templates = [
    "default-deny-all",
    "allow-dns",
    "allow-monitoring"
  ]
}
```

### Storage Module

**Purpose**: Manages storage provisioning and classes

#### Features

- **Local Path Provisioner**: Local storage management
- **Storage Classes**: Multiple storage tiers
- **NFS Integration**: Network-attached storage
- **Backup Integration**: Automated backup configuration

#### Usage

```hcl
module "storage" {
  source = "./modules/storage"
  
  # Local Path Provisioner
  enable_local_path_provisioner = true
  local_path_config = {
    path         = "/opt/local-path-provisioner"
    helper_image = "busybox:latest"
  }
  
  # Storage Classes
  storage_classes = [
    {
      name                = "fast-ssd"
      provisioner        = "rancher.io/local-path"
      volume_binding_mode = "WaitForFirstConsumer"
      parameters = {
        path = "/mnt/fast-ssd"
      }
    },
    {
      name                = "standard"
      provisioner        = "rancher.io/local-path"
      volume_binding_mode = "WaitForFirstConsumer"
      is_default         = true
    }
  ]
  
  # NFS Configuration
  enable_nfs_provisioner = true
  nfs_config = {
    server = "192.168.16.100"
    path   = "/mnt/nfs-storage"
    storage_class = "nfs"
  }
  
  environment = var.environment
}
```

## Environment Management

### Development Environment

**File**: `environments/development/main.tf`

```hcl
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
  
  backend "local" {
    path = "terraform.tfstate"
  }
}

# Local provider configuration for development
provider "kubernetes" {
  config_path = "~/.kube/config"
}

provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}

# Development-specific configuration
module "k3s_cluster" {
  source = "../../modules/k3s-cluster"
  
  cluster_name = "homelab-dev"
  environment  = "development"
  
  # Minimal resources for development
  master_nodes = [
    {
      name = "dev-master"
      ip   = "192.168.16.26"
    }
  ]
  
  # Development-specific settings
  disable_traefik   = true
  disable_servicelb = true
  enable_rootless   = false  # Easier debugging
}

module "networking" {
  source = "../../modules/networking"
  
  environment = "development"
  
  metallb_ip_pools = {
    development = {
      addresses = ["192.168.25.200-192.168.25.210"]
    }
  }
  
  # Relaxed policies for development
  enable_network_policies = false
}

module "security" {
  source = "../../modules/security"
  
  environment = "development"
  
  # Use staging Let's Encrypt for development
  letsencrypt_config = {
    email  = "tz-dev@vectorweight.com"
    server = "https://acme-staging-v02.api.letsencrypt.org/directory"
  }
  
  # Permissive security for development
  pod_security_config = {
    enforce = "baseline"
    audit   = "restricted"
    warn    = "restricted"
  }
}

module "storage" {
  source = "../../modules/storage"
  
  environment = "development"
  
  # Single storage class for development
  storage_classes = [
    {
      name       = "local-path"
      is_default = true
    }
  ]
}
```

### Production Environment

**File**: `environments/production/main.tf`

```hcl
terraform {
  required_version = ">= 1.0"
  
  backend "s3" {
    bucket         = "homelab-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

# Production-specific configuration
module "k3s_cluster" {
  source = "../../modules/k3s-cluster"
  
  cluster_name = "homelab-prod"
  environment  = "production"
  
  # High availability configuration
  master_nodes = [
    {
      name = "prod-master-1"
      ip   = "192.168.16.26"
    },
    {
      name = "prod-master-2"
      ip   = "192.168.16.27"
    },
    {
      name = "prod-master-3"
      ip   = "192.168.16.28"
    }
  ]
  
  # Production hardening
  enable_rootless = true
  extra_server_args = [
    "--disable=metrics-server",
    "--audit-log-path=/var/log/k3s-audit.log",
    "--audit-log-maxage=30"
  ]
}

module "networking" {
  source = "../../modules/networking"
  
  environment = "production"
  
  metallb_ip_pools = {
    production = {
      addresses = ["192.168.25.240-192.168.25.250"]
    }
  }
  
  # Strict network policies
  enable_network_policies = true
  default_deny_all       = true
  
  # Service mesh for production
  enable_istio = true
  istio_config = {
    enable_mtls = true
  }
}

module "security" {
  source = "../../modules/security"
  
  environment = "production"
  
  # Production Let's Encrypt
  letsencrypt_config = {
    email  = "tz-dev@vectorweight.com"
    server = "https://acme-v02.api.letsencrypt.org/directory"
  }
  
  # Strict security policies
  pod_security_config = {
    enforce = "restricted"
    audit   = "restricted"
    warn    = "restricted"
  }
  
  # Runtime security monitoring
  enable_falco = true
}

module "storage" {
  source = "../../modules/storage"
  
  environment = "production"
  
  # Multiple storage tiers
  storage_classes = [
    {
      name                = "fast-ssd"
      provisioner        = "rancher.io/local-path"
      volume_binding_mode = "WaitForFirstConsumer"
      parameters = {
        path = "/mnt/fast-ssd"
      }
    },
    {
      name       = "standard"
      is_default = true
    },
    {
      name        = "backup"
      provisioner = "nfs.csi.k8s.io"
      parameters = {
        server = "192.168.16.100"
        share  = "/mnt/backup"
      }
    }
  ]
}
```

## Integration Patterns

### Terraform + Helm Integration

Terraform manages infrastructure while Helm manages applications:

```hcl
# Terraform manages the infrastructure
resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = "monitoring"
    labels = {
      "terraform" = "true"
      "tier"      = "monitoring"
    }
  }
}

# Helm manages the application deployment
resource "helm_release" "prometheus" {
  name       = "prometheus"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = "55.0.0"
  namespace  = kubernetes_namespace.monitoring.metadata[0].name
  
  values = [
    file("${path.module}/templates/prometheus-values.yaml")
  ]
  
  depends_on = [
    kubernetes_namespace.monitoring
  ]
}
```

### Terraform + GitOps Integration

Terraform provisions infrastructure, GitOps manages continuous deployment:

```hcl
# Terraform provisions ArgoCD
resource "helm_release" "argocd" {
  name       = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = "5.51.0"
  namespace  = "argocd"
  
  create_namespace = true
  
  values = [
    templatefile("${path.module}/templates/argocd-values.yaml", {
      hostname = "argocd.${var.domain}"
    })
  ]
}

# ArgoCD Application for infrastructure components
resource "kubernetes_manifest" "infrastructure_app" {
  manifest = {
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "Application"
    metadata = {
      name      = "infrastructure"
      namespace = "argocd"
    }
    spec = {
      project = "default"
      source = {
        repoURL        = "https://github.com/tzervas/homelab-infra"
        targetRevision = "main"
        path           = "kubernetes/infrastructure"
      }
      destination = {
        server    = "https://kubernetes.default.svc"
        namespace = "default"
      }
      syncPolicy = {
        automated = {
          prune    = true
          selfHeal = true
        }
      }
    }
  }
  
  depends_on = [helm_release.argocd]
}
```

### Remote State Management

#### S3 Backend Configuration

```hcl
terraform {
  backend "s3" {
    bucket         = "homelab-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    versioning     = true
    dynamodb_table = "terraform-state-locks"
    
    # Optional: KMS encryption key
    kms_key_id = "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012"
  }
}
```

#### Local Backend for Development

```hcl
terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}
```

#### HTTP Backend for Team Collaboration

```hcl
terraform {
  backend "http" {
    address        = "https://gitlab.homelab.local/api/v4/projects/1/terraform/state/production"
    lock_address   = "https://gitlab.homelab.local/api/v4/projects/1/terraform/state/production/lock"
    unlock_address = "https://gitlab.homelab.local/api/v4/projects/1/terraform/state/production/lock"
    username       = "terraform"
    password       = var.gitlab_token
    lock_method    = "POST"
    unlock_method  = "DELETE"
    retry_wait_min = 5
  }
}
```

## Operational Patterns

### Workspace Management

#### Environment Isolation

```bash
# Create workspace for environment
terraform workspace new production
terraform workspace select production

# List workspaces
terraform workspace list

# Show current workspace
terraform workspace show
```

#### Variable Management per Workspace

```hcl
# terraform.tfvars
environment = terraform.workspace

# Conditional configuration based on workspace
locals {
  environment_config = {
    development = {
      instance_count = 1
      instance_size  = "small"
    }
    production = {
      instance_count = 3
      instance_size  = "large"
    }
  }
  
  current_config = local.environment_config[terraform.workspace]
}
```

### Module Versioning

```hcl
module "k3s_cluster" {
  source  = "git::https://github.com/tzervas/terraform-k3s-module.git?ref=v2.1.0"
  # or
  source  = "./modules/k3s-cluster"
  
  # Version constraints for remote modules
  version = "~> 2.1"
}
```

### Automated Validation

#### CI/CD Pipeline Integration

```yaml
# .github/workflows/terraform.yml
name: Terraform

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  terraform:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Terraform
      uses: hashicorp/setup-terraform@v2
      with:
        terraform_version: 1.6.0
    
    - name: Terraform Format
      run: terraform fmt -check -recursive
    
    - name: Terraform Init
      run: terraform init
    
    - name: Terraform Validate
      run: terraform validate
    
    - name: Terraform Plan
      run: terraform plan -no-color
      
    - name: Terraform Apply
      if: github.ref == 'refs/heads/main'
      run: terraform apply -auto-approve
```

#### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/antonbabenko/pre-commit-terraform
    rev: v1.83.0
    hooks:
      - id: terraform_fmt
      - id: terraform_validate
      - id: terraform_docs
      - id: terraform_tflint
      - id: terrascan
        args:
          - --args=--policy-type=k8s
```

### Testing Strategies

#### Unit Testing with Terratest

```go
// test/terraform_test.go
package test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/terraform"
    "github.com/stretchr/testify/assert"
)

func TestTerraformK3sModule(t *testing.T) {
    terraformOptions := &terraform.Options{
        TerraformDir: "../modules/k3s-cluster",
        Vars: map[string]interface{}{
            "cluster_name": "test-cluster",
            "environment":  "test",
        },
    }

    defer terraform.Destroy(t, terraformOptions)
    terraform.InitAndApply(t, terraformOptions)

    clusterName := terraform.Output(t, terraformOptions, "cluster_name")
    assert.Equal(t, "test-cluster", clusterName)
}
```

#### Integration Testing

```bash
#!/bin/bash
# scripts/test-terraform-integration.sh

set -e

echo "Running Terraform integration tests..."

# Test development environment
cd terraform/environments/development
terraform init
terraform plan -detailed-exitcode
terraform apply -auto-approve

# Validate cluster
kubectl cluster-info
kubectl get nodes

# Test networking
kubectl apply -f ../../../testing/network-test.yaml
kubectl wait --for=condition=ready pod/network-test --timeout=300s

# Cleanup
terraform destroy -auto-approve
```

## Monitoring and Observability

### Terraform State Monitoring

```hcl
# Prometheus metrics for Terraform state
resource "kubernetes_config_map" "terraform_metrics" {
  metadata {
    name      = "terraform-metrics"
    namespace = "monitoring"
  }
  
  data = {
    "terraform-exporter.yml" = yamlencode({
      terraform_state_files = [
        "/terraform/state/development.tfstate",
        "/terraform/state/production.tfstate"
      ]
      metrics_port = 9090
    })
  }
}
```

### Drift Detection

```bash
#!/bin/bash
# scripts/drift-detection.sh

# Check for configuration drift
terraform plan -detailed-exitcode

exit_code=$?

if [ $exit_code -eq 1 ]; then
    echo "ERROR: Terraform plan failed"
    exit 1
elif [ $exit_code -eq 2 ]; then
    echo "WARNING: Configuration drift detected"
    
    # Send alert
    curl -X POST "$SLACK_WEBHOOK_URL" \
         -H 'Content-type: application/json' \
         --data '{"text":"🚨 Terraform configuration drift detected in '"$ENVIRONMENT"'"}'
    
    # Optionally auto-remediate
    if [ "$AUTO_REMEDIATE" = "true" ]; then
        terraform apply -auto-approve
    fi
fi
```

## Security Best Practices

### Sensitive Data Management

```hcl
# Use Terraform variables for sensitive data
variable "database_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# Store in Kubernetes secrets
resource "kubernetes_secret" "database" {
  metadata {
    name      = "database-credentials"
    namespace = "default"
  }
  
  data = {
    username = "admin"
    password = var.database_password
  }
  
  type = "Opaque"
}
```

### RBAC Integration

```hcl
# Terraform service account with minimal permissions
resource "kubernetes_service_account" "terraform" {
  metadata {
    name      = "terraform"
    namespace = "kube-system"
  }
}

resource "kubernetes_cluster_role" "terraform" {
  metadata {
    name = "terraform"
  }
  
  rule {
    api_groups = [""]
    resources  = ["namespaces", "configmaps", "secrets"]
    verbs      = ["get", "list", "create", "update", "patch", "delete"]
  }
  
  rule {
    api_groups = ["apps"]
    resources  = ["deployments", "daemonsets", "statefulsets"]
    verbs      = ["get", "list", "create", "update", "patch", "delete"]
  }
}

resource "kubernetes_cluster_role_binding" "terraform" {
  metadata {
    name = "terraform"
  }
  
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.terraform.metadata[0].name
  }
  
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.terraform.metadata[0].name
    namespace = kubernetes_service_account.terraform.metadata[0].namespace
  }
}
```

## Troubleshooting

### Common Issues

#### State Lock Issues

```bash
# Force unlock state (use with caution)
terraform force-unlock LOCK_ID

# Check lock information
terraform show terraform.tfstate | grep serial
```

#### Provider Authentication Issues

```bash
# Debug provider configuration
TF_LOG=DEBUG terraform plan

# Verify kubeconfig
kubectl config current-context
kubectl cluster-info
```

#### Module Resolution Issues

```bash
# Clear module cache
rm -rf .terraform/modules/

# Re-initialize modules
terraform init -upgrade
```

### Debugging Commands

```bash
# Enable debug logging
export TF_LOG=DEBUG
export TF_LOG_PATH=terraform.log

# Validate configuration
terraform validate

# Check configuration syntax
terraform fmt -check -recursive

# Show planned changes
terraform plan -out=tfplan
terraform show tfplan

# Inspect state
terraform state list
terraform state show resource.name

# Import existing resources
terraform import resource.name existing-id
```

## Performance Optimization

### Parallelism

```bash
# Increase parallelism for large infrastructures
terraform plan -parallelism=20
terraform apply -parallelism=20
```

### Resource Targeting

```bash
# Apply specific resources
terraform apply -target=module.networking
terraform apply -target=kubernetes_namespace.monitoring

# Refresh specific resources
terraform refresh -target=helm_release.prometheus
```

### State Optimization

```bash
# Remove unused resources from state
terraform state rm resource.unused

# Move resources between modules
terraform state mv module.old.resource module.new.resource
```

## Integration with Existing Tools

### Ansible Integration

```hcl
# Use Terraform to provision infrastructure
# Use Ansible for configuration management
resource "local_file" "ansible_inventory" {
  content = templatefile("${path.module}/templates/inventory.tpl", {
    masters = module.k3s_cluster.master_nodes
    workers = module.k3s_cluster.worker_nodes
  })
  filename = "${path.root}/ansible/inventory/terraform.yml"
}

# Trigger Ansible playbook after infrastructure provisioning
resource "null_resource" "ansible_provisioning" {
  provisioner "local-exec" {
    command = "ansible-playbook -i ${local_file.ansible_inventory.filename} site.yml"
    working_dir = "${path.root}/ansible"
  }
  
  depends_on = [
    module.k3s_cluster,
    local_file.ansible_inventory
  ]
}
```

### GitOps Integration

```hcl
# Terraform manages infrastructure
# GitOps manages applications
resource "kubernetes_manifest" "gitops_applications" {
  for_each = var.gitops_applications
  
  manifest = {
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "Application"
    metadata = {
      name      = each.key
      namespace = "argocd"
    }
    spec = each.value
  }
  
  depends_on = [helm_release.argocd]
}
```

## Conclusion

This Terraform integration provides a robust foundation for Infrastructure as Code in the homelab environment. Key benefits include:

- **Consistency**: Reproducible infrastructure across environments
- **Collaboration**: Team-based infrastructure management with version control
- **Security**: RBAC integration and sensitive data protection
- **Scalability**: Modular architecture supporting growth
- **Integration**: Seamless integration with existing tools and workflows

The modular approach allows for gradual adoption and customization based on specific requirements while maintaining best practices for security, performance, and maintainability.

---

**Document Version:** 2.0  
**Last Updated:** December 2024  
**Next Review:** Quarterly  
**Maintainer:** Infrastructure Team  
**Contact:** tz-dev@vectorweight.com
