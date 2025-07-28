# Custom Homelab Provider Configuration
# This file defines custom resources and data sources specific to homelab environments

terraform {
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
}

# Custom resource for homelab configuration management
resource "local_file" "homelab_inventory" {
  filename = "${path.root}/../config/homelab-inventory.yaml"
  content = templatefile("${path.module}/templates/homelab-inventory.yaml.tpl", {
    timestamp = timestamp()
    terraform_workspace = terraform.workspace
    infrastructure_components = var.infrastructure_components
  })
  
  file_permission = "0644"
}

# Custom data source for homelab network discovery
data "external" "network_discovery" {
  program = ["bash", "${path.module}/scripts/network-discovery.sh"]
}

# Custom resource for homelab service registry
resource "local_file" "service_registry" {
  filename = "${path.root}/../config/service-registry.yaml"
  content = templatefile("${path.module}/templates/service-registry.yaml.tpl", {
    services = var.homelab_services
    network_info = data.external.network_discovery.result
  })
  
  file_permission = "0644"
}

# Variables for custom provider
variable "infrastructure_components" {
  description = "Infrastructure components deployed in the homelab"
  type = map(object({
    name        = string
    version     = string
    namespace   = string
    enabled     = bool
    endpoints   = list(string)
    dependencies = list(string)
  }))
  default = {}
}

variable "homelab_services" {
  description = "Services running in the homelab"
  type = map(object({
    name        = string
    type        = string
    port        = number
    protocol    = string
    health_check = string
    tags        = list(string)
  }))
  default = {}
}

# Outputs for custom provider
output "homelab_inventory_path" {
  description = "Path to the homelab inventory file"
  value       = local_file.homelab_inventory.filename
}

output "network_discovery_results" {
  description = "Results from network discovery"
  value       = data.external.network_discovery.result
}

output "service_registry_path" {
  description = "Path to the service registry file"
  value       = local_file.service_registry.filename
}
