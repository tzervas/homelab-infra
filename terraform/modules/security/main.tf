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
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

# Cert-Manager for SSL certificate management
resource "helm_release" "cert_manager" {
  count = var.enable_cert_manager ? 1 : 0

  name       = "cert-manager"
  repository = "https://charts.jetstack.io"
  chart      = "cert-manager"
  version    = var.cert_manager_version
  namespace  = var.cert_manager_namespace

  create_namespace = true

  set {
    name  = "installCRDs"
    value = "true"
  }

  set {
    name  = "global.leaderElection.namespace"
    value = var.cert_manager_namespace
  }

  values = [
    templatefile("${path.module}/templates/cert-manager-values.yaml.tpl", {
      prometheus_monitoring = var.prometheus_monitoring
      log_level             = var.log_level
    })
  ]
}

# ClusterIssuer for Let's Encrypt
resource "kubernetes_manifest" "letsencrypt_staging" {
  count = var.enable_cert_manager && var.enable_letsencrypt ? 1 : 0

  manifest = {
    apiVersion = "cert-manager.io/v1"
    kind       = "ClusterIssuer"
    metadata = {
      name = "letsencrypt-staging"
    }
    spec = {
      acme = {
        server = "https://acme-staging-v02.api.letsencrypt.org/directory"
        email  = var.letsencrypt_email
        privateKeySecretRef = {
          name = "letsencrypt-staging"
        }
        solvers = [
          {
            http01 = {
              ingress = {
                class = "nginx"
              }
            }
          }
        ]
      }
    }
  }

  depends_on = [helm_release.cert_manager]
}

resource "kubernetes_manifest" "letsencrypt_production" {
  count = var.enable_cert_manager && var.enable_letsencrypt ? 1 : 0

  manifest = {
    apiVersion = "cert-manager.io/v1"
    kind       = "ClusterIssuer"
    metadata = {
      name = "letsencrypt-production"
    }
    spec = {
      acme = {
        server = "https://acme-v02.api.letsencrypt.org/directory"
        email  = var.letsencrypt_email
        privateKeySecretRef = {
          name = "letsencrypt-production"
        }
        solvers = [
          {
            http01 = {
              ingress = {
                class = "nginx"
              }
            }
          }
        ]
      }
    }
  }

  depends_on = [helm_release.cert_manager]
}

# External Secrets Operator
resource "helm_release" "external_secrets" {
  count = var.enable_external_secrets ? 1 : 0

  name       = "external-secrets"
  repository = "https://charts.external-secrets.io"
  chart      = "external-secrets"
  version    = var.external_secrets_version
  namespace  = var.external_secrets_namespace

  create_namespace = true

  values = [
    templatefile("${path.module}/templates/external-secrets-values.yaml.tpl", {
      prometheus_monitoring = var.prometheus_monitoring
      log_level             = var.log_level
    })
  ]
}

# Sealed Secrets Controller
resource "helm_release" "sealed_secrets" {
  count = var.enable_sealed_secrets ? 1 : 0

  name       = "sealed-secrets"
  repository = "https://bitnami-labs.github.io/sealed-secrets"
  chart      = "sealed-secrets"
  version    = var.sealed_secrets_version
  namespace  = var.sealed_secrets_namespace

  create_namespace = true

  values = [
    templatefile("${path.module}/templates/sealed-secrets-values.yaml.tpl", {
      prometheus_monitoring = var.prometheus_monitoring
    })
  ]
}

# RBAC Configuration
resource "kubernetes_cluster_role" "homelab_admin" {
  count = var.enable_rbac ? 1 : 0

  metadata {
    name = "homelab:admin"
    labels = {
      "app.kubernetes.io/name"       = "homelab-rbac"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  rule {
    api_groups = ["*"]
    resources  = ["*"]
    verbs      = ["*"]
  }
}

resource "kubernetes_cluster_role" "homelab_viewer" {
  count = var.enable_rbac ? 1 : 0

  metadata {
    name = "homelab:viewer"
    labels = {
      "app.kubernetes.io/name"       = "homelab-rbac"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  rule {
    api_groups = [""]
    resources  = ["pods", "services", "endpoints", "persistentvolumeclaims", "events", "configmaps", "secrets"]
    verbs      = ["get", "list", "watch"]
  }

  rule {
    api_groups = ["apps"]
    resources  = ["deployments", "daemonsets", "replicasets", "statefulsets"]
    verbs      = ["get", "list", "watch"]
  }

  rule {
    api_groups = ["networking.k8s.io"]
    resources  = ["ingresses", "networkpolicies"]
    verbs      = ["get", "list", "watch"]
  }
}

# Pod Security Standards
resource "kubernetes_manifest" "pod_security_policy" {
  for_each = var.enable_pod_security ? var.pod_security_policies : {}

  manifest = {
    apiVersion = "v1"
    kind       = "Namespace"
    metadata = {
      name = each.key
      labels = {
        "pod-security.kubernetes.io/enforce" = each.value.enforce
        "pod-security.kubernetes.io/audit"   = each.value.audit
        "pod-security.kubernetes.io/warn"    = each.value.warn
      }
    }
  }
}

# Network Policies
resource "kubernetes_network_policy" "deny_all_ingress" {
  for_each = var.enable_network_policies ? toset(var.secured_namespaces) : []

  metadata {
    name      = "deny-all-ingress"
    namespace = each.value
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress"]
  }
}

resource "kubernetes_network_policy" "allow_kube_system" {
  for_each = var.enable_network_policies ? toset(var.secured_namespaces) : []

  metadata {
    name      = "allow-kube-system"
    namespace = each.value
  }

  spec {
    pod_selector {}
    policy_types = ["Egress"]

    egress {
      to {
        namespace_selector {
          match_labels = {
            name = "kube-system"
          }
        }
      }
    }
  }
}

# Security Context Constraints (for OpenShift-like behavior)
resource "kubernetes_manifest" "security_context_constraint" {
  for_each = var.enable_security_constraints ? var.security_constraints : {}

  manifest = {
    apiVersion = "security.openshift.io/v1"
    kind       = "SecurityContextConstraints"
    metadata = {
      name = each.key
    }
    allowHostDirVolumePlugin = lookup(each.value, "allow_host_dir_volume", false)
    allowHostIPC             = lookup(each.value, "allow_host_ipc", false)
    allowHostNetwork         = lookup(each.value, "allow_host_network", false)
    allowHostPID             = lookup(each.value, "allow_host_pid", false)
    allowHostPorts           = lookup(each.value, "allow_host_ports", false)
    allowPrivilegedContainer = lookup(each.value, "allow_privileged", false)
    allowedCapabilities      = lookup(each.value, "allowed_capabilities", [])
    defaultAddCapabilities   = lookup(each.value, "default_add_capabilities", [])
    requiredDropCapabilities = lookup(each.value, "required_drop_capabilities", ["ALL"])
    runAsUser = {
      type = lookup(each.value, "run_as_user_type", "MustRunAsRange")
    }
    seLinuxContext = {
      type = lookup(each.value, "selinux_context_type", "MustRunAs")
    }
    fsGroup = {
      type = lookup(each.value, "fs_group_type", "MustRunAs")
    }
  }
}

# Falco Security Runtime
resource "helm_release" "falco" {
  count = var.enable_falco ? 1 : 0

  name       = "falco"
  repository = "https://falcosecurity.github.io/charts"
  chart      = "falco"
  version    = var.falco_version
  namespace  = var.falco_namespace

  create_namespace = true

  values = [
    templatefile("${path.module}/templates/falco-values.yaml.tpl", {
      prometheus_monitoring = var.prometheus_monitoring
      log_level             = var.log_level
      enable_syscall_source = var.falco_syscall_source
    })
  ]
}
