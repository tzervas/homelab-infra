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

# Local Path Provisioner (for local storage)
resource "kubernetes_manifest" "local_path_provisioner" {
  count = var.enable_local_path_provisioner ? 1 : 0
  
  manifest = {
    apiVersion = "apps/v1"
    kind       = "Deployment"
    metadata = {
      name      = "local-path-provisioner"
      namespace = var.storage_namespace
    }
    spec = {
      replicas = 1
      selector = {
        matchLabels = {
          app = "local-path-provisioner"
        }
      }
      template = {
        metadata = {
          labels = {
            app = "local-path-provisioner"
          }
        }
        spec = {
          serviceAccountName = "local-path-provisioner-service-account"
          containers = [
            {
              name  = "local-path-provisioner"
              image = "rancher/local-path-provisioner:${var.local_path_provisioner_version}"
              command = [
                "local-path-provisioner",
                "--debug",
                "start",
                "--config",
                "/etc/config/config.json"
              ]
              volumeMounts = [
                {
                  name      = "config-volume"
                  mountPath = "/etc/config/"
                }
              ]
              env = [
                {
                  name  = "POD_NAMESPACE"
                  valueFrom = {
                    fieldRef = {
                      fieldPath = "metadata.namespace"
                    }
                  }
                }
              ]
            }
          ]
          volumes = [
            {
              name = "config-volume"
              configMap = {
                name = "local-path-config"
              }
            }
          ]
        }
      }
    }
  }
  
  depends_on = [kubernetes_namespace.storage_namespace]
}

# Storage namespace
resource "kubernetes_namespace" "storage_namespace" {
  count = var.enable_local_path_provisioner ? 1 : 0
  
  metadata {
    name = var.storage_namespace
    labels = {
      "app.kubernetes.io/name"       = "storage-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}

# Storage Classes
resource "kubernetes_storage_class" "local_path" {
  count = var.enable_local_path_provisioner ? 1 : 0
  
  metadata {
    name = "local-path"
    annotations = {
      "storageclass.kubernetes.io/is-default-class" = var.set_local_path_default ? "true" : "false"
    }
  }
  
  storage_provisioner    = "rancher.io/local-path"
  volume_binding_mode    = "WaitForFirstConsumer"
  allow_volume_expansion = true
  reclaim_policy         = "Delete"
}

resource "kubernetes_storage_class" "fast_ssd" {
  count = var.enable_fast_ssd_class ? 1 : 0
  
  metadata {
    name = "fast-ssd"
    annotations = {
      "storageclass.kubernetes.io/is-default-class" = "false"
    }
  }
  
  storage_provisioner    = "rancher.io/local-path"
  volume_binding_mode    = "WaitForFirstConsumer"
  allow_volume_expansion = true
  reclaim_policy         = "Retain"
  
  parameters = {
    "path" = var.fast_ssd_path
  }
}

# Persistent Volume Claims for common services
resource "kubernetes_persistent_volume_claim" "default_pvcs" {
  for_each = var.default_pvcs
  
  metadata {
    name      = each.key
    namespace = each.value.namespace
    labels    = each.value.labels
  }
  
  spec {
    access_modes       = each.value.access_modes
    storage_class_name = each.value.storage_class
    
    resources {
      requests = {
        storage = each.value.size
      }
    }
  }
  
  depends_on = [kubernetes_storage_class.local_path]
}

# NFS Support (if enabled)
resource "kubernetes_manifest" "nfs_provisioner" {
  count = var.enable_nfs_provisioner ? 1 : 0
  
  manifest = {
    apiVersion = "apps/v1"
    kind       = "Deployment"
    metadata = {
      name      = "nfs-client-provisioner"
      namespace = var.storage_namespace
    }
    spec = {
      replicas = 1
      selector = {
        matchLabels = {
          app = "nfs-client-provisioner"
        }
      }
      strategy = {
        type = "Recreate"
      }
      template = {
        metadata = {
          labels = {
            app = "nfs-client-provisioner"
          }
        }
        spec = {
          serviceAccountName = "nfs-client-provisioner"
          containers = [
            {
              name  = "nfs-client-provisioner"
              image = "gcr.io/k8s-staging-sig-storage/nfs-subdir-external-provisioner:v4.0.2"
              volumeMounts = [
                {
                  name      = "nfs-client-root"
                  mountPath = "/persistentvolumes"
                }
              ]
              env = [
                {
                  name  = "PROVISIONER_NAME"
                  value = "homelab.local/nfs"
                },
                {
                  name  = "NFS_SERVER"
                  value = var.nfs_server
                },
                {
                  name  = "NFS_PATH"
                  value = var.nfs_path
                }
              ]
            }
          ]
          volumes = [
            {
              name = "nfs-client-root"
              nfs = {
                server = var.nfs_server
                path   = var.nfs_path
              }
            }
          ]
        }
      }
    }
  }
  
  depends_on = [kubernetes_namespace.storage_namespace]
}

resource "kubernetes_storage_class" "nfs" {
  count = var.enable_nfs_provisioner ? 1 : 0
  
  metadata {
    name = "nfs"
  }
  
  storage_provisioner    = "homelab.local/nfs"
  volume_binding_mode    = "Immediate"
  allow_volume_expansion = true
  reclaim_policy         = "Delete"
  
  parameters = {
    "archiveOnDelete" = "false"
  }
}
