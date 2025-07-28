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

# MetalLB Load Balancer configuration
resource "helm_release" "metallb" {
  count = var.enable_metallb ? 1 : 0
  
  name       = "metallb"
  repository = "https://metallb.github.io/metallb"
  chart      = "metallb"
  version    = var.metallb_version
  namespace  = var.metallb_namespace
  
  create_namespace = true
  
  values = [
    templatefile("${path.module}/templates/metallb-values.yaml.tpl", {
      prometheus_monitoring = var.prometheus_monitoring
      log_level            = var.log_level
    })
  ]
  
  depends_on = [kubernetes_namespace.metallb_namespace]
}

# MetalLB namespace
resource "kubernetes_namespace" "metallb_namespace" {
  count = var.enable_metallb ? 1 : 0
  
  metadata {
    name = var.metallb_namespace
    labels = {
      "app.kubernetes.io/name"       = "metallb-system"
      "app.kubernetes.io/managed-by" = "terraform"
      "pod-security.kubernetes.io/enforce" = "privileged"
      "pod-security.kubernetes.io/audit"   = "privileged"
      "pod-security.kubernetes.io/warn"    = "privileged"
    }
  }
}

# MetalLB IP Address Pool
resource "kubernetes_manifest" "metallb_ipaddresspool" {
  for_each = var.enable_metallb ? var.ip_pools : {}
  
  manifest = {
    apiVersion = "metallb.io/v1beta1"
    kind       = "IPAddressPool"
    metadata = {
      name      = each.key
      namespace = var.metallb_namespace
    }
    spec = {
      addresses = each.value.addresses
      autoAssign = lookup(each.value, "auto_assign", true)
      avoidBuggyIPs = lookup(each.value, "avoid_buggy_ips", false)
    }
  }
  
  depends_on = [helm_release.metallb]
}

# MetalLB L2 Advertisement
resource "kubernetes_manifest" "metallb_l2advertisement" {
  for_each = var.enable_metallb ? var.l2_advertisements : {}
  
  manifest = {
    apiVersion = "metallb.io/v1beta1"
    kind       = "L2Advertisement"
    metadata = {
      name      = each.key
      namespace = var.metallb_namespace
    }
    spec = {
      ipAddressPools = lookup(each.value, "ip_address_pools", [])
      nodeSelectors  = lookup(each.value, "node_selectors", [])
      interfaces     = lookup(each.value, "interfaces", [])
    }
  }
  
  depends_on = [kubernetes_manifest.metallb_ipaddresspool]
}

# Network Policies
resource "kubernetes_network_policy" "default_deny_all" {
  count = var.enable_network_policies ? 1 : 0
  
  metadata {
    name      = "default-deny-all"
    namespace = "default"
  }
  
  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}

resource "kubernetes_network_policy" "allow_dns" {
  count = var.enable_network_policies ? 1 : 0
  
  metadata {
    name      = "allow-dns"
    namespace = "default"
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
        pod_selector {
          match_labels = {
            "k8s-app" = "kube-dns"
          }
        }
      }
      ports {
        protocol = "UDP"
        port     = "53"
      }
      ports {
        protocol = "TCP"
        port     = "53"
      }
    }
  }
}

# CoreDNS configuration
resource "kubernetes_config_map" "coredns_custom" {
  count = var.enable_custom_dns ? 1 : 0
  
  metadata {
    name      = "coredns-custom"
    namespace = "kube-system"
  }
  
  data = {
    "custom.server" = templatefile("${path.module}/templates/coredns-custom.conf.tpl", {
      custom_dns_entries = var.custom_dns_entries
      upstream_dns       = var.upstream_dns_servers
    })
  }
}

# Ingress Controller (Nginx)
resource "helm_release" "nginx_ingress" {
  count = var.enable_nginx_ingress ? 1 : 0
  
  name       = "nginx-ingress"
  repository = "https://kubernetes.github.io/ingress-nginx"
  chart      = "ingress-nginx"
  version    = var.nginx_ingress_version
  namespace  = var.nginx_ingress_namespace
  
  create_namespace = true
  
  values = [
    templatefile("${path.module}/templates/nginx-ingress-values.yaml.tpl", {
      service_type              = var.nginx_service_type
      load_balancer_ip         = var.nginx_load_balancer_ip
      enable_ssl_passthrough   = var.nginx_ssl_passthrough
      default_ssl_certificate  = var.nginx_default_ssl_cert
      enable_metrics          = var.prometheus_monitoring
    })
  ]
  
  depends_on = [helm_release.metallb]
}

# Multus CNI for additional network interfaces
resource "kubernetes_manifest" "multus_cni" {
  count = var.enable_multus ? 1 : 0
  
  manifest = {
    apiVersion = "apiextensions.k8s.io/v1"
    kind       = "CustomResourceDefinition"
    metadata = {
      name = "network-attachment-definitions.k8s.cni.cncf.io"
    }
    spec = {
      group = "k8s.cni.cncf.io"
      scope = "Namespaced"
      names = {
        plural   = "network-attachment-definitions"
        singular = "network-attachment-definition"
        kind     = "NetworkAttachmentDefinition"
        shortNames = ["net-attach-def"]
      }
      versions = [{
        name    = "v1"
        served  = true
        storage = true
        schema = {
          openAPIV3Schema = {
            type = "object"
            properties = {
              spec = {
                type = "object"
                properties = {
                  config = {
                    type = "string"
                  }
                }
              }
            }
          }
        }
      }]
    }
  }
}
