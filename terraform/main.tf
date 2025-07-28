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
    external = {
      source  = "hashicorp/external"
      version = "~> 2.3"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

# This is the root Terraform configuration for the homelab infrastructure
# It provides a unified entry point for managing the entire infrastructure

# Variables for environment selection
variable "environment" {
  description = "Environment to deploy (development, staging, production)"
  type        = string
  default     = "development"
  
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "kubeconfig_path" {
  description = "Path to kubeconfig file"
  type        = string
  default     = "~/.kube/config"
}

# Provider configuration
provider "kubernetes" {
  config_path = var.kubeconfig_path
}

provider "helm" {
  kubernetes {
    config_path = var.kubeconfig_path
  }
}

# Local variables for environment-specific configuration
locals {
  environment_configs = {
    development = {
      cluster_name     = "homelab-dev"
      enable_monitoring = false
      enable_security  = false
      resource_limits  = "minimal"
    }
    staging = {
      cluster_name     = "homelab-staging"
      enable_monitoring = true
      enable_security  = true
      resource_limits  = "moderate"
    }
    production = {
      cluster_name     = "homelab-prod"
      enable_monitoring = true
      enable_security  = true
      resource_limits  = "full"
    }
  }
  
  current_config = local.environment_configs[var.environment]
}

# Environment-specific module instantiation
module "homelab_infrastructure" {
  source = "./environments/${var.environment}"
  
  # Pass common variables
  kubeconfig_path = var.kubeconfig_path
  
  # Environment-specific overrides can be added here
  cluster_name = local.current_config.cluster_name
}

# Output the environment configuration
output "environment" {
  description = "Current environment configuration"
  value = {
    environment = var.environment
    config     = local.current_config
  }
}

output "cluster_info" {
  description = "Cluster information"
  value = {
    name     = local.current_config.cluster_name
    endpoint = try(module.homelab_infrastructure.cluster_endpoint, "")
  }
  sensitive = true
}

output "infrastructure_summary" {
  description = "Summary of deployed infrastructure components"
  value = {
    k3s_cluster = try(module.homelab_infrastructure.k3s_status, {})
    networking  = try(module.homelab_infrastructure.networking_summary, {})
    security    = try(module.homelab_infrastructure.security_summary, {})
    storage     = try(module.homelab_infrastructure.storage_summary, {})
  }
}
