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
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
}

# Provider configuration - uses local kubeconfig
provider "kubernetes" {
  config_path = var.kubeconfig_path
}

provider "helm" {
  kubernetes {
    config_path = var.kubeconfig_path
  }
}

# K3s Cluster Module
module "k3s_cluster" {
  source = "../../modules/k3s-cluster"

  cluster_name         = var.cluster_name
  k3s_version         = var.k3s_version
  cluster_cidr        = var.cluster_cidr
  service_cidr        = var.service_cidr
  cluster_dns         = var.cluster_dns
  disable_components  = var.disable_components
  node_labels         = var.node_labels
  node_taints         = var.node_taints
  extra_args          = var.extra_args
  rootless            = var.rootless_mode
  flannel_backend     = var.flannel_backend
  log_level           = var.log_level
}

# Networking Module
module "networking" {
  source = "../../modules/networking"

  # MetalLB Configuration
  enable_metallb       = var.enable_metallb
  metallb_version     = var.metallb_version
  ip_pools            = var.metallb_ip_pools
  l2_advertisements   = var.metallb_l2_advertisements

  # Ingress Configuration
  enable_nginx_ingress     = var.enable_nginx_ingress
  nginx_ingress_version   = var.nginx_ingress_version
  nginx_service_type      = var.nginx_service_type
  nginx_load_balancer_ip  = var.nginx_load_balancer_ip
  nginx_ssl_passthrough   = var.nginx_ssl_passthrough

  # DNS Configuration
  enable_custom_dns       = var.enable_custom_dns
  custom_dns_entries     = var.custom_dns_entries
  upstream_dns_servers   = var.upstream_dns_servers

  # Network Policies
  enable_network_policies = var.enable_network_policies

  # CNI Configuration
  cni_type    = var.cni_type
  pod_cidr    = var.cluster_cidr

  # Monitoring
  prometheus_monitoring = var.enable_monitoring
  log_level            = var.log_level

  depends_on = [module.k3s_cluster]
}

# Security Module
module "security" {
  source = "../../modules/security"

  # Cert-Manager
  enable_cert_manager      = var.enable_cert_manager
  cert_manager_version    = var.cert_manager_version
  enable_letsencrypt      = var.enable_letsencrypt
  letsencrypt_email       = var.letsencrypt_email

  # Secret Management
  enable_external_secrets = var.enable_external_secrets
  enable_sealed_secrets   = var.enable_sealed_secrets

  # RBAC
  enable_rbac = var.enable_rbac

  # Pod Security
  enable_pod_security     = var.enable_pod_security
  pod_security_policies  = var.pod_security_policies

  # Network Policies
  enable_network_policies = var.enable_network_policies
  secured_namespaces     = var.secured_namespaces

  # Runtime Security
  enable_falco           = var.enable_falco
  falco_syscall_source  = var.falco_syscall_source

  # Monitoring
  prometheus_monitoring = var.enable_monitoring
  log_level            = var.log_level

  depends_on = [module.networking]
}

# Storage Module
module "storage" {
  source = "../../modules/storage"

  # Local Path Provisioner
  enable_local_path_provisioner = var.enable_local_path_provisioner
  local_path_provisioner_version = var.local_path_provisioner_version
  set_local_path_default        = var.set_local_path_default

  # Fast SSD Storage Class
  enable_fast_ssd_class = var.enable_fast_ssd_class
  fast_ssd_path        = var.fast_ssd_path

  # NFS Support
  enable_nfs_provisioner = var.enable_nfs_provisioner
  nfs_server            = var.nfs_server
  nfs_path              = var.nfs_path

  # Default PVCs
  default_pvcs = var.default_pvcs

  # Storage namespace
  storage_namespace = var.storage_namespace

  depends_on = [module.k3s_cluster]
}

# Integration with existing config structure
data "local_file" "existing_config" {
  filename = "../../../config/environments/development/.gitkeep"
}

# Create integration file for existing config system
resource "local_file" "terraform_integration" {
  filename = "../../../config/environments/development/terraform-integration.yaml"
  content = templatefile("${path.module}/templates/integration.yaml.tpl", {
    cluster_name          = module.k3s_cluster.cluster_name
    cluster_endpoint      = module.k3s_cluster.cluster_endpoint
    metallb_ip_pools     = module.networking.metallb_ip_pools
    ingress_namespace    = module.networking.nginx_ingress_namespace
    cert_manager_enabled = module.security.cert_manager_enabled
    storage_classes      = module.storage.storage_classes
  })
}
