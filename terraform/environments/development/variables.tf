# Development Environment Variables

# General Configuration
variable "cluster_name" {
  description = "Name of the K3s cluster"
  type        = string
  default     = "homelab-dev"
}

variable "kubeconfig_path" {
  description = "Path to kubeconfig file"
  type        = string
  default     = "~/.kube/config"
}

variable "log_level" {
  description = "Global log level"
  type        = string
  default     = "info"
}

# K3s Configuration
variable "k3s_version" {
  description = "K3s version to install"
  type        = string
  default     = "v1.28.8+k3s1"
}

variable "cluster_cidr" {
  description = "CIDR range for cluster pods"
  type        = string
  default     = "10.42.0.0/16"
}

variable "service_cidr" {
  description = "CIDR range for cluster services"
  type        = string
  default     = "10.43.0.0/16"
}

variable "cluster_dns" {
  description = "Cluster DNS server IP"
  type        = string
  default     = "10.43.0.10"
}

variable "disable_components" {
  description = "K3s components to disable"
  type        = list(string)
  default     = ["traefik", "servicelb"]
}

variable "node_labels" {
  description = "Labels to apply to nodes"
  type        = map(string)
  default = {
    "environment" = "development"
    "node-type"   = "homelab"
  }
}

variable "node_taints" {
  description = "Taints to apply to nodes"
  type        = list(string)
  default     = []
}

variable "extra_args" {
  description = "Extra arguments for K3s"
  type        = list(string)
  default     = []
}

variable "rootless_mode" {
  description = "Enable rootless mode"
  type        = bool
  default     = false
}

variable "flannel_backend" {
  description = "Flannel backend to use"
  type        = string
  default     = "vxlan"
}

variable "cni_type" {
  description = "CNI plugin type"
  type        = string
  default     = "flannel"
}

# MetalLB Configuration
variable "enable_metallb" {
  description = "Enable MetalLB load balancer"
  type        = bool
  default     = true
}

variable "metallb_version" {
  description = "MetalLB version"
  type        = string
  default     = "0.13.12"
}

variable "metallb_ip_pools" {
  description = "MetalLB IP address pools"
  type = map(object({
    addresses       = list(string)
    auto_assign     = optional(bool, true)
    avoid_buggy_ips = optional(bool, false)
  }))
  default = {
    development = {
      addresses = ["192.168.1.240-192.168.1.245"]
    }
  }
}

variable "metallb_l2_advertisements" {
  description = "MetalLB L2 advertisements"
  type = map(object({
    ip_address_pools = optional(list(string), [])
    node_selectors   = optional(list(map(string)), [])
    interfaces       = optional(list(string), [])
  }))
  default = {
    development = {
      ip_address_pools = ["development"]
    }
  }
}

# Ingress Configuration
variable "enable_nginx_ingress" {
  description = "Enable Nginx ingress controller"
  type        = bool
  default     = true
}

variable "nginx_ingress_version" {
  description = "Nginx ingress controller version"
  type        = string
  default     = "4.8.3"
}

variable "nginx_service_type" {
  description = "Nginx service type"
  type        = string
  default     = "LoadBalancer"
}

variable "nginx_load_balancer_ip" {
  description = "Static IP for Nginx load balancer"
  type        = string
  default     = ""
}

variable "nginx_ssl_passthrough" {
  description = "Enable SSL passthrough"
  type        = bool
  default     = true
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

# Security Configuration
variable "enable_cert_manager" {
  description = "Enable cert-manager"
  type        = bool
  default     = false # Disabled in development
}

variable "cert_manager_version" {
  description = "Cert-manager version"
  type        = string
  default     = "v1.13.2"
}

variable "enable_letsencrypt" {
  description = "Enable Let's Encrypt integration"
  type        = bool
  default     = false
}

variable "letsencrypt_email" {
  description = "Email for Let's Encrypt"
  type        = string
  default     = ""
}

variable "enable_external_secrets" {
  description = "Enable External Secrets Operator"
  type        = bool
  default     = false
}

variable "enable_sealed_secrets" {
  description = "Enable Sealed Secrets"
  type        = bool
  default     = false
}

variable "enable_rbac" {
  description = "Enable RBAC configuration"
  type        = bool
  default     = true
}

variable "enable_pod_security" {
  description = "Enable Pod Security Standards"
  type        = bool
  default     = false # Relaxed in development
}

variable "pod_security_policies" {
  description = "Pod security policies per namespace"
  type = map(object({
    enforce = string
    audit   = string
    warn    = string
  }))
  default = {}
}

variable "enable_network_policies" {
  description = "Enable network policies"
  type        = bool
  default     = false # Disabled in development for easier debugging
}

variable "secured_namespaces" {
  description = "Namespaces to apply security policies to"
  type        = list(string)
  default     = ["default", "kube-system"]
}

variable "enable_falco" {
  description = "Enable Falco runtime security"
  type        = bool
  default     = false # Disabled in development
}

variable "falco_syscall_source" {
  description = "Enable Falco syscall source"
  type        = bool
  default     = false
}

# Storage Configuration
variable "enable_local_path_provisioner" {
  description = "Enable local path provisioner"
  type        = bool
  default     = true
}

variable "local_path_provisioner_version" {
  description = "Local path provisioner version"
  type        = string
  default     = "v0.0.24"
}

variable "set_local_path_default" {
  description = "Set local path as default storage class"
  type        = bool
  default     = true
}

variable "enable_fast_ssd_class" {
  description = "Enable fast SSD storage class"
  type        = bool
  default     = false
}

variable "fast_ssd_path" {
  description = "Path for fast SSD storage"
  type        = string
  default     = "/opt/local-path-provisioner/fast-ssd"
}

variable "enable_nfs_provisioner" {
  description = "Enable NFS provisioner"
  type        = bool
  default     = false
}

variable "nfs_server" {
  description = "NFS server address"
  type        = string
  default     = ""
}

variable "nfs_path" {
  description = "NFS path"
  type        = string
  default     = ""
}

variable "storage_namespace" {
  description = "Storage system namespace"
  type        = string
  default     = "storage-system"
}

variable "default_pvcs" {
  description = "Default PVCs to create"
  type = map(object({
    namespace     = string
    size          = string
    access_modes  = list(string)
    storage_class = string
    labels        = map(string)
  }))
  default = {}
}

# Monitoring Configuration
variable "enable_monitoring" {
  description = "Enable Prometheus monitoring"
  type        = bool
  default     = false # Can be enabled as needed in development
}
