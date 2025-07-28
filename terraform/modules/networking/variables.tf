# Networking Module Variables

# MetalLB Configuration
variable "enable_metallb" {
  description = "Enable MetalLB load balancer"
  type        = bool
  default     = true
}

variable "metallb_version" {
  description = "MetalLB Helm chart version"
  type        = string
  default     = "0.13.12"
}

variable "metallb_namespace" {
  description = "Namespace for MetalLB"
  type        = string
  default     = "metallb-system"
}

variable "ip_pools" {
  description = "MetalLB IP address pools configuration"
  type = map(object({
    addresses        = list(string)
    auto_assign      = optional(bool, true)
    avoid_buggy_ips  = optional(bool, false)
  }))
  default = {
    default = {
      addresses = ["192.168.1.240-192.168.1.250"]
    }
  }
}

variable "l2_advertisements" {
  description = "MetalLB L2 advertisement configuration"
  type = map(object({
    ip_address_pools = optional(list(string), [])
    node_selectors   = optional(list(map(string)), [])
    interfaces       = optional(list(string), [])
  }))
  default = {
    default = {
      ip_address_pools = ["default"]
    }
  }
}

# Network Policies
variable "enable_network_policies" {
  description = "Enable default network policies"
  type        = bool
  default     = false
}

# DNS Configuration
variable "enable_custom_dns" {
  description = "Enable custom DNS configuration"
  type        = bool
  default     = false
}

variable "custom_dns_entries" {
  description = "Custom DNS entries"
  type = map(object({
    ip   = string
    type = optional(string, "A")
  }))
  default = {}
}

variable "upstream_dns_servers" {
  description = "Upstream DNS servers"
  type        = list(string)
  default     = ["8.8.8.8", "8.8.4.4"]
}

# Ingress Controller
variable "enable_nginx_ingress" {
  description = "Enable Nginx ingress controller"
  type        = bool
  default     = true
}

variable "nginx_ingress_version" {
  description = "Nginx ingress controller Helm chart version"
  type        = string
  default     = "4.8.3"
}

variable "nginx_ingress_namespace" {
  description = "Namespace for Nginx ingress controller"
  type        = string
  default     = "ingress-nginx"
}

variable "nginx_service_type" {
  description = "Service type for Nginx ingress controller"
  type        = string
  default     = "LoadBalancer"
  
  validation {
    condition     = contains(["ClusterIP", "NodePort", "LoadBalancer"], var.nginx_service_type)
    error_message = "Service type must be one of: ClusterIP, NodePort, LoadBalancer."
  }
}

variable "nginx_load_balancer_ip" {
  description = "Static IP for Nginx load balancer"
  type        = string
  default     = ""
}

variable "nginx_ssl_passthrough" {
  description = "Enable SSL passthrough for Nginx"
  type        = bool
  default     = true
}

variable "nginx_default_ssl_cert" {
  description = "Default SSL certificate for Nginx"
  type        = string
  default     = ""
}

# Multus CNI
variable "enable_multus" {
  description = "Enable Multus CNI for multiple network interfaces"
  type        = bool
  default     = false
}

# Monitoring
variable "prometheus_monitoring" {
  description = "Enable Prometheus monitoring"
  type        = bool
  default     = false
}

variable "log_level" {
  description = "Log level for networking components"
  type        = string
  default     = "info"
  
  validation {
    condition     = contains(["error", "warn", "info", "debug"], var.log_level)
    error_message = "Log level must be one of: error, warn, info, debug."
  }
}

# VLAN Configuration
variable "vlan_interfaces" {
  description = "VLAN interface configurations"
  type = map(object({
    parent_interface = string
    vlan_id         = number
    ip_range        = string
  }))
  default = {}
}

# Service Mesh
variable "enable_service_mesh" {
  description = "Enable service mesh (Istio/Linkerd)"
  type        = bool
  default     = false
}

variable "service_mesh_type" {
  description = "Type of service mesh to deploy"
  type        = string
  default     = "istio"
  
  validation {
    condition     = contains(["istio", "linkerd", "consul"], var.service_mesh_type)
    error_message = "Service mesh type must be one of: istio, linkerd, consul."
  }
}

# CNI Configuration
variable "cni_type" {
  description = "CNI plugin type"
  type        = string
  default     = "flannel"
  
  validation {
    condition     = contains(["flannel", "calico", "cilium", "weave"], var.cni_type)
    error_message = "CNI type must be one of: flannel, calico, cilium, weave."
  }
}

variable "pod_cidr" {
  description = "Pod CIDR range"
  type        = string
  default     = "10.42.0.0/16"
  
  validation {
    condition     = can(cidrhost(var.pod_cidr, 0))
    error_message = "Pod CIDR must be a valid CIDR block."
  }
}
