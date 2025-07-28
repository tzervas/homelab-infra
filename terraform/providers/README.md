# Provider descriptions and integration templates

# MetalLB templates

file_add_description "terraform/modules/networking/templates/metallb-values.yaml.tpl" "Values template for configuring MetalLB Helm chart."

# NGINX Ingress templates

file_add_description "terraform/modules/networking/templates/nginx-ingress-values.yaml.tpl" "Values template for configuring NGINX Ingress Controller Helm chart."

# CoreDNS custom configuration template

file_add_description "terraform/modules/networking/templates/coredns-custom.conf.tpl" "Template for custom CoreDNS configuration."

# Security templates

# Cert-Manager values template

file_add_description "terraform/modules/security/templates/cert-manager-values.yaml.tpl" "Values template for configuring Cert-Manager Helm chart."

# External Secrets Operator values template

file_add_description "terraform/modules/security/templates/external-secrets-values.yaml.tpl" "Values template for configuring External Secrets Operator Helm chart."

# Sealed Secrets values template

file_add_description "terraform/modules/security/templates/sealed-secrets-values.yaml.tpl" "Values template for configuring Sealed Secrets Helm chart."

# Storage templates

# No custom templates needed

# Integration templates for each environment

file_add_description "terraform/environments/templates/integration.yaml.tpl" "Environment-specific integration template."
