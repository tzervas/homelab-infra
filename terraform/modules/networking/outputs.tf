# Networking Module Outputs

# MetalLB Outputs
output "metallb_namespace" {
  description = "MetalLB namespace"
  value       = var.enable_metallb ? var.metallb_namespace : null
}

output "metallb_ip_pools" {
  description = "MetalLB IP address pools"
  value       = var.enable_metallb ? var.ip_pools : {}
}

output "metallb_status" {
  description = "MetalLB deployment status"
  value = var.enable_metallb ? {
    installed = true
    version   = var.metallb_version
    namespace = var.metallb_namespace
    } : {
    installed = false
    version   = null
    namespace = null
  }
}

# Ingress Controller Outputs
output "nginx_ingress_namespace" {
  description = "Nginx ingress controller namespace"
  value       = var.enable_nginx_ingress ? var.nginx_ingress_namespace : null
}

output "nginx_ingress_service_type" {
  description = "Nginx ingress controller service type"
  value       = var.enable_nginx_ingress ? var.nginx_service_type : null
}

output "nginx_ingress_load_balancer_ip" {
  description = "Nginx ingress controller load balancer IP"
  value       = var.enable_nginx_ingress ? var.nginx_load_balancer_ip : null
}

output "nginx_ingress_status" {
  description = "Nginx ingress controller deployment status"
  value = var.enable_nginx_ingress ? {
    installed       = true
    version         = var.nginx_ingress_version
    namespace       = var.nginx_ingress_namespace
    service_type    = var.nginx_service_type
    ssl_passthrough = var.nginx_ssl_passthrough
    } : {
    installed = false
    version   = null
    namespace = null
  }
}

# DNS Configuration Outputs
output "custom_dns_enabled" {
  description = "Whether custom DNS is enabled"
  value       = var.enable_custom_dns
}

output "custom_dns_entries" {
  description = "Custom DNS entries"
  value       = var.enable_custom_dns ? var.custom_dns_entries : {}
}

output "upstream_dns_servers" {
  description = "Upstream DNS servers"
  value       = var.upstream_dns_servers
}

# Network Policy Outputs
output "network_policies_enabled" {
  description = "Whether network policies are enabled"
  value       = var.enable_network_policies
}

# CNI Configuration Outputs
output "cni_type" {
  description = "CNI plugin type in use"
  value       = var.cni_type
}

output "pod_cidr" {
  description = "Pod CIDR range"
  value       = var.pod_cidr
}

# Service Mesh Outputs
output "service_mesh_enabled" {
  description = "Whether service mesh is enabled"
  value       = var.enable_service_mesh
}

output "service_mesh_type" {
  description = "Type of service mesh deployed"
  value       = var.enable_service_mesh ? var.service_mesh_type : null
}

# Multus CNI Outputs
output "multus_enabled" {
  description = "Whether Multus CNI is enabled"
  value       = var.enable_multus
}

# VLAN Configuration Outputs
output "vlan_interfaces" {
  description = "VLAN interface configurations"
  value       = var.vlan_interfaces
}

# Monitoring Outputs
output "prometheus_monitoring_enabled" {
  description = "Whether Prometheus monitoring is enabled"
  value       = var.prometheus_monitoring
}

output "log_level" {
  description = "Log level for networking components"
  value       = var.log_level
}

# Networking Summary
output "networking_summary" {
  description = "Summary of networking configuration"
  value = {
    metallb = {
      enabled   = var.enable_metallb
      version   = var.metallb_version
      namespace = var.metallb_namespace
      ip_pools  = var.ip_pools
    }
    ingress = {
      enabled      = var.enable_nginx_ingress
      version      = var.nginx_ingress_version
      namespace    = var.nginx_ingress_namespace
      service_type = var.nginx_service_type
    }
    dns = {
      custom_enabled   = var.enable_custom_dns
      upstream_servers = var.upstream_dns_servers
    }
    cni = {
      type     = var.cni_type
      pod_cidr = var.pod_cidr
    }
    security = {
      network_policies = var.enable_network_policies
      service_mesh     = var.enable_service_mesh
    }
    monitoring = {
      prometheus = var.prometheus_monitoring
      log_level  = var.log_level
    }
  }
}
