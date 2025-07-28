terraform {
  required_version = ">= 1.0"
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
    external = {
      source  = "hashicorp/external"
      version = "~> 2.3"
    }
  }
}

# K3s cluster configuration variables
variable "cluster_name" {
  description = "Name of the K3s cluster"
  type        = string
  default     = "homelab-k3s"
}

variable "node_count" {
  description = "Number of nodes in the cluster"
  type        = number
  default     = 1
}

variable "k3s_version" {
  description = "Version of K3s to install"
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

# Generate K3s installation script
resource "local_file" "k3s_install_script" {
  filename = "${path.module}/k3s-install.sh"
  content = templatefile("${path.module}/templates/k3s-install.sh.tpl", {
    cluster_name      = var.cluster_name
    k3s_version      = var.k3s_version
    cluster_cidr     = var.cluster_cidr
    service_cidr     = var.service_cidr
    cluster_dns      = var.cluster_dns
    disable_components = join(",", var.disable_components)
    node_taints      = join(",", var.node_taints)
    node_labels      = join(",", [for k, v in var.node_labels : "${k}=${v}"])
    extra_args       = join(" ", var.extra_args)
  })

  provisioner "local-exec" {
    command = "chmod +x ${self.filename}"
  }
}

# Generate K3s configuration
resource "local_file" "k3s_config" {
  filename = "${path.module}/k3s-config.yaml"
  content = templatefile("${path.module}/templates/k3s-config.yaml.tpl", {
    cluster_cidr     = var.cluster_cidr
    service_cidr     = var.service_cidr
    cluster_dns      = var.cluster_dns
    disable_components = var.disable_components
    node_taints      = var.node_taints
    node_labels      = var.node_labels
    extra_args       = var.extra_args
  })
}

# Generate kubeconfig template
resource "local_file" "kubeconfig_template" {
  filename = "${path.module}/kubeconfig-template.yaml"
  content = templatefile("${path.module}/templates/kubeconfig.yaml.tpl", {
    cluster_name = var.cluster_name
  })
}

# Data source to check if K3s is running
data "external" "k3s_status" {
  program = ["bash", "${path.module}/scripts/check-k3s-status.sh"]

  depends_on = [local_file.k3s_install_script]
}
