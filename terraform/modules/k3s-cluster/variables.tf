# K3s Cluster Module Variables

variable "cluster_name" {
  description = "Name of the K3s cluster"
  type        = string
  default     = "homelab-k3s"
  
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.cluster_name))
    error_message = "Cluster name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "node_count" {
  description = "Number of nodes in the cluster"
  type        = number
  default     = 1
  
  validation {
    condition     = var.node_count > 0 && var.node_count <= 10
    error_message = "Node count must be between 1 and 10."
  }
}

variable "k3s_version" {
  description = "Version of K3s to install"
  type        = string
  default     = "v1.28.8+k3s1"
  
  validation {
    condition     = can(regex("^v[0-9]+\\.[0-9]+\\.[0-9]+\\+k3s[0-9]+$", var.k3s_version))
    error_message = "K3s version must follow the format vX.Y.Z+k3sN."
  }
}

variable "cluster_cidr" {
  description = "CIDR range for cluster pods"
  type        = string
  default     = "10.42.0.0/16"
  
  validation {
    condition     = can(cidrhost(var.cluster_cidr, 0))
    error_message = "Cluster CIDR must be a valid CIDR block."
  }
}

variable "service_cidr" {
  description = "CIDR range for cluster services"
  type        = string
  default     = "10.43.0.0/16"
  
  validation {
    condition     = can(cidrhost(var.service_cidr, 0))
    error_message = "Service CIDR must be a valid CIDR block."
  }
}

variable "cluster_dns" {
  description = "Cluster DNS server IP"
  type        = string
  default     = "10.43.0.10"
  
  validation {
    condition     = can(regex("^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$", var.cluster_dns))
    error_message = "Cluster DNS must be a valid IP address."
  }
}

variable "disable_components" {
  description = "List of K3s components to disable"
  type        = list(string)
  default     = ["traefik", "servicelb"]
}

variable "node_taints" {
  description = "Taints to apply to nodes"
  type        = list(string)
  default     = []
}

variable "node_labels" {
  description = "Labels to apply to nodes"
  type        = map(string)
  default     = {}
}

variable "extra_args" {
  description = "Extra arguments for K3s server"
  type        = list(string)
  default     = []
}

variable "data_dir" {
  description = "Directory to store K3s data"
  type        = string
  default     = "/var/lib/rancher/k3s"
}

variable "config_file" {
  description = "Path to K3s configuration file"
  type        = string
  default     = "/etc/rancher/k3s/config.yaml"
}

variable "token_file" {
  description = "Path to K3s token file"
  type        = string
  default     = "/var/lib/rancher/k3s/server/token"
}

variable "kubeconfig_file" {
  description = "Path to kubeconfig file"
  type        = string
  default     = "/etc/rancher/k3s/k3s.yaml"
}

variable "log_level" {
  description = "Log level for K3s"
  type        = string
  default     = "info"
  
  validation {
    condition     = contains(["panic", "fatal", "error", "warn", "info", "debug", "trace"], var.log_level)
    error_message = "Log level must be one of: panic, fatal, error, warn, info, debug, trace."
  }
}

variable "snapshotter" {
  description = "Snapshotter to use (native or overlayfs)"
  type        = string
  default     = "overlayfs"
  
  validation {
    condition     = contains(["native", "overlayfs"], var.snapshotter)
    error_message = "Snapshotter must be either 'native' or 'overlayfs'."
  }
}

variable "rootless" {
  description = "Enable rootless mode"
  type        = bool
  default     = false
}

variable "write_kubeconfig_mode" {
  description = "Permissions for kubeconfig file"
  type        = string
  default     = "0644"
}

variable "flannel_backend" {
  description = "Flannel backend to use"
  type        = string
  default     = "vxlan"
  
  validation {
    condition     = contains(["none", "vxlan", "ipsec", "host-gw", "wireguard"], var.flannel_backend)
    error_message = "Flannel backend must be one of: none, vxlan, ipsec, host-gw, wireguard."
  }
}
