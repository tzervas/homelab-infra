# K3s Cluster Module Outputs

output "cluster_name" {
  description = "Name of the K3s cluster"
  value       = var.cluster_name
}

output "cluster_endpoint" {
  description = "K3s cluster API endpoint"
  value       = "https://127.0.0.1:6443"
}

output "kubeconfig_path" {
  description = "Path to the kubeconfig file"
  value       = var.kubeconfig_file
}

output "cluster_ca_certificate" {
  description = "Base64 encoded cluster CA certificate"
  value       = try(data.external.k3s_status.result["ca_cert"], "")
  sensitive   = true
}

output "cluster_token" {
  description = "K3s cluster token"
  value       = try(data.external.k3s_status.result["token"], "")
  sensitive   = true
}

output "cluster_status" {
  description = "Status of the K3s cluster"
  value       = try(data.external.k3s_status.result["status"], "unknown")
}

output "install_script_path" {
  description = "Path to the K3s installation script"
  value       = local_file.k3s_install_script.filename
}

output "config_file_path" {
  description = "Path to the K3s configuration file"
  value       = local_file.k3s_config.filename
}

output "cluster_cidr" {
  description = "CIDR range for cluster pods"
  value       = var.cluster_cidr
}

output "service_cidr" {
  description = "CIDR range for cluster services"
  value       = var.service_cidr
}

output "cluster_dns" {
  description = "Cluster DNS server IP"
  value       = var.cluster_dns
}

output "disabled_components" {
  description = "List of disabled K3s components"
  value       = var.disable_components
}

output "node_labels" {
  description = "Labels applied to nodes"
  value       = var.node_labels
}

output "node_taints" {
  description = "Taints applied to nodes"
  value       = var.node_taints
}

output "k3s_version" {
  description = "Version of K3s installed"
  value       = var.k3s_version
}

output "data_directory" {
  description = "K3s data directory"
  value       = var.data_dir
}

output "flannel_backend" {
  description = "Flannel backend in use"
  value       = var.flannel_backend
}

output "rootless_mode" {
  description = "Whether rootless mode is enabled"
  value       = var.rootless
}
