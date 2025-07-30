#!/bin/bash

# Homelab Infrastructure Deployment with Keycloak SSO
# This script orchestrates the deployment of all components in the correct order
# with comprehensive Keycloak SSO integration

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/logs/homelab-sso-deployment-$(date +%Y%m%d_%H%M%S).log"
LOAD_BALANCER_IP="192.168.16.100"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case $level in
        "INFO")  echo -e "${GREEN}[INFO]${NC} $message" | tee -a "$LOG_FILE" ;;
        "WARN")  echo -e "${YELLOW}[WARN]${NC} $message" | tee -a "$LOG_FILE" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} $message" | tee -a "$LOG_FILE" ;;
        "DEBUG") echo -e "${BLUE}[DEBUG]${NC} $message" | tee -a "$LOG_FILE" ;;
    esac
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Cleanup function
cleanup() {
    log "INFO" "Cleaning up temporary files..."
    # Add any cleanup logic here
}

# Signal handlers
trap cleanup EXIT
trap 'log "ERROR" "Deployment interrupted by user"; exit 130' INT TERM

# Create logs directory
mkdir -p "${SCRIPT_DIR}/logs"

# Health check function
wait_for_pod_ready() {
    local namespace=$1
    local selector=$2
    local timeout=${3:-300}

    log "INFO" "Waiting for pods with selector '$selector' in namespace '$namespace' to be ready..."

    if kubectl wait --for=condition=ready pod -l "$selector" -n "$namespace" --timeout="${timeout}s"; then
        log "INFO" "Pods are ready: $selector"
        return 0
    else
        log "ERROR" "Timeout waiting for pods: $selector"
        return 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites..."

    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log "ERROR" "kubectl is not installed or not in PATH"
        exit 1
    fi

    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log "ERROR" "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    # Check if required files exist
    local required_files=(
        "kubernetes/base/namespaces.yaml"
        "kubernetes/base/keycloak-deployment.yaml"
        "kubernetes/base/oauth2-proxy.yaml"
        "kubernetes/base/grafana-deployment.yaml"
        "kubernetes/base/gitlab-deployment.yaml"
        "kubernetes/base/prometheus-deployment.yaml"
        "kubernetes/base/ollama-webui-deployment.yaml"
        "kubernetes/base/jupyterlab-deployment.yaml"
        "kubernetes/base/landing-page.yaml"
    )

    for file in "${required_files[@]}"; do
        if [[ ! -f "${SCRIPT_DIR}/${file}" ]]; then
            log "ERROR" "Required file not found: ${file}"
            exit 1
        fi
    done

    log "INFO" "Prerequisites check passed"
}

# Deploy core infrastructure
deploy_core_infrastructure() {
    log "INFO" "Deploying core infrastructure..."

    # Deploy namespaces first
    kubectl apply -f "${SCRIPT_DIR}/kubernetes/base/namespaces.yaml"

    # Deploy cert-manager and cluster issuers
    if [[ -f "${SCRIPT_DIR}/kubernetes/base/cluster-issuers.yaml" ]]; then
        kubectl apply -f "${SCRIPT_DIR}/kubernetes/base/cluster-issuers.yaml"
    fi

    log "INFO" "Core infrastructure deployed"
}

# Deploy Keycloak
deploy_keycloak() {
    log "INFO" "Deploying Keycloak..."

    kubectl apply -f "${SCRIPT_DIR}/kubernetes/base/keycloak-deployment.yaml"

    # Wait for Keycloak to be ready
    wait_for_pod_ready "keycloak" "app=keycloak" 600

    log "INFO" "Keycloak deployment completed"
}

# Deploy OAuth2 Proxy
deploy_oauth2_proxy() {
    log "INFO" "Deploying OAuth2 Proxy..."

    kubectl apply -f "${SCRIPT_DIR}/kubernetes/base/oauth2-proxy.yaml"

    # Wait for OAuth2 Proxy to be ready
    wait_for_pod_ready "oauth2-proxy" "app=oauth2-proxy" 300

    log "INFO" "OAuth2 Proxy deployment completed"
}

# Deploy application services
deploy_applications() {
    log "INFO" "Deploying application services..."

    # Deploy services in parallel but wait for each to be ready
    local services=(
        "monitoring:grafana-deployment.yaml:app=grafana"
        "monitoring:prometheus-deployment.yaml:app=prometheus"
        "gitlab:gitlab-deployment.yaml:app=gitlab"
        "ai-tools:ollama-webui-deployment.yaml:app=ollama"
        "jupyter:jupyterlab-deployment.yaml:app=jupyterlab"
        "homelab-portal:landing-page.yaml:app=landing-page"
    )

    for service in "${services[@]}"; do
        IFS=':' read -r namespace file selector <<< "$service"

        log "INFO" "Deploying $file..."
        kubectl apply -f "${SCRIPT_DIR}/kubernetes/base/${file}"

        # Wait for the service to be ready
        wait_for_pod_ready "$namespace" "$selector" 600
    done

    log "INFO" "All application services deployed"
}

# Configure GitLab Runner with ARC
deploy_gitlab_runner() {
    log "INFO" "Setting up GitLab Runner with Actions Runner Controller..."

    # Check if ARC is already installed
    if ! kubectl get namespace actions-runner-system &> /dev/null; then
        log "INFO" "Installing Actions Runner Controller..."

        # Install ARC using Helm
        helm repo add actions-runner-controller https://actions-runner-controller.github.io/actions-runner-controller
        helm repo update

        helm install actions-runner-controller actions-runner-controller/actions-runner-controller \\
            --namespace actions-runner-system \\
            --create-namespace \\
            --set syncPeriod=1m

        wait_for_pod_ready "actions-runner-system" "app.kubernetes.io/name=actions-runner-controller" 300
    fi

    # Create GitLab Runner configuration
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: gitlab-runner-token
  namespace: gitlab
type: Opaque
stringData:
  token: "REPLACE_WITH_GITLAB_RUNNER_TOKEN"
---
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerDeployment
metadata:
  name: gitlab-runner
  namespace: gitlab
spec:
  replicas: 2
  template:
    spec:
      repository: homelab/infrastructure
      env:
      - name: GITLAB_URL
        value: "https://gitlab.homelab.local"
      - name: REGISTRATION_TOKEN
        valueFrom:
          secretKeyRef:
            name: gitlab-runner-token
            key: token
      dockerdWithinRunnerContainer: true
      image: summerwind/actions-runner:latest
      resources:
        requests:
          memory: "1Gi"
          cpu: "500m"
        limits:
          memory: "2Gi"
          cpu: "1000m"
EOF

    log "INFO" "GitLab Runner with ARC configured (manual token configuration required)"
}

# Health checks and validation
perform_health_checks() {
    log "INFO" "Performing comprehensive health checks..."

    # Check all ingress endpoints
    local endpoints=(
        "https://auth.homelab.local"
        "https://homelab.local"
        "https://grafana.homelab.local"
        "https://prometheus.homelab.local"
        "https://gitlab.homelab.local"
        "https://ollama.homelab.local"
        "https://jupyter.homelab.local"
    )

    log "INFO" "Checking ingress endpoints..."
    for endpoint in "${endpoints[@]}"; do
        if curl -k -s --max-time 10 "$endpoint" > /dev/null; then
            log "INFO" "✅ $endpoint is accessible"
        else
            log "WARN" "⚠️  $endpoint is not responding"
        fi
    done

    # Check LoadBalancer status
    log "INFO" "Checking LoadBalancer status..."
    kubectl get svc -A | grep LoadBalancer

    # Check certificate status
    log "INFO" "Checking certificate status..."
    kubectl get certificates -A

    # Check OAuth2 Proxy logs for any authentication issues
    log "INFO" "Checking OAuth2 Proxy status..."
    kubectl logs -n oauth2-proxy -l app=oauth2-proxy --tail=10

    log "INFO" "Health checks completed"
}

# Update health monitor script
enhance_health_monitor() {
    log "INFO" "Enhancing health monitor script..."

    local health_script="${SCRIPT_DIR}/scripts/health-monitor.sh"

    if [[ -f "$health_script" ]]; then
        # Backup existing script
        cp "$health_script" "${health_script}.backup.$(date +%Y%m%d_%H%M%S)"

        # Add authentication validation to health monitor
        cat >> "$health_script" << 'EOF'

# Keycloak authentication validation
check_keycloak_auth() {
    echo "Checking Keycloak authentication..."

    # Check Keycloak realm endpoint
    if curl -k -s --max-time 10 "https://auth.homelab.local/realms/homelab" | grep -q "homelab"; then
        echo "✅ Keycloak realm is accessible"
    else
        echo "❌ Keycloak realm check failed"
        return 1
    fi

    # Check OAuth2 Proxy health
    if kubectl get pods -n oauth2-proxy -l app=oauth2-proxy --field-selector=status.phase=Running | grep -q Running; then
        echo "✅ OAuth2 Proxy is running"
    else
        echo "❌ OAuth2 Proxy is not running properly"
        return 1
    fi

    return 0
}

# Certificate validity check
check_certificates() {
    echo "Checking certificate validity..."

    local domains=("auth.homelab.local" "homelab.local" "grafana.homelab.local" "prometheus.homelab.local" "gitlab.homelab.local" "ollama.homelab.local" "jupyter.homelab.local")

    for domain in "${domains[@]}"; do
        if echo | openssl s_client -connect "${domain}:443" -servername "$domain" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null; then
            echo "✅ Certificate for $domain is valid"
        else
            echo "⚠️  Certificate check failed for $domain"
        fi
    done
}

# Add authentication checks to main health check function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    check_keycloak_auth
    check_certificates
fi
EOF

        log "INFO" "Health monitor script enhanced with authentication validation"
    else
        log "WARN" "Health monitor script not found, skipping enhancement"
    fi
}

# Display access information
display_access_info() {
    log "INFO" "Deployment completed successfully!"

    cat << EOF

🎉 HOMELAB INFRASTRUCTURE WITH KEYCLOAK SSO DEPLOYED! 🎉

📍 LoadBalancer IP: ${LOAD_BALANCER_IP}

🔐 Authentication:
   • Primary Auth: https://auth.homelab.local
   • Admin User: admin / homelab123!
   • All services protected by Keycloak SSO via OAuth2 Proxy

🌐 Service Access URLs:
   • 🏠 Portal: https://homelab.local
   • 📊 Grafana: https://grafana.homelab.local
   • 🔍 Prometheus: https://prometheus.homelab.local
   • 🚀 GitLab: https://gitlab.homelab.local
   • 🤖 Ollama+WebUI: https://ollama.homelab.local
   • 📓 JupyterLab: https://jupyter.homelab.local

📋 Setup Instructions:
   1. Add DNS entries to your /etc/hosts file:
      sudo bash -c 'cat >> /etc/hosts << EOL
${LOAD_BALANCER_IP} homelab.local
${LOAD_BALANCER_IP} auth.homelab.local
${LOAD_BALANCER_IP} grafana.homelab.local
${LOAD_BALANCER_IP} prometheus.homelab.local
${LOAD_BALANCER_IP} gitlab.homelab.local
${LOAD_BALANCER_IP} ollama.homelab.local
${LOAD_BALANCER_IP} jupyter.homelab.local
EOL'

   2. Install CA certificate (optional, for trusted HTTPS):
      kubectl get secret homelab-ca-issuer -n cert-manager -o jsonpath='{.data.tls\.crt}' | base64 -d > homelab-ca.crt
      sudo cp homelab-ca.crt /usr/local/share/ca-certificates/
      sudo update-ca-certificates

   3. Access the portal at https://homelab.local
      - You'll be redirected to Keycloak for authentication
      - Use admin/homelab123! to login
      - After authentication, you'll see the homelab portal

🔧 Post-Deployment Tasks:
   • Configure GitLab Runner token in GitLab admin panel
   • Set up Grafana data sources (Prometheus will auto-configure)
   • Configure Ollama models as needed
   • Set up JupyterLab notebooks and kernels

📊 Monitoring:
   • Check deployment status: kubectl get pods -A
   • View ingress status: kubectl get ingress -A
   • Monitor certificates: kubectl get certificates -A
   • Run health checks: ./scripts/health-monitor.sh

For troubleshooting, check the deployment log: ${LOG_FILE}

EOF
}

# Main deployment function
main() {
    log "INFO" "Starting Homelab Infrastructure Deployment with Keycloak SSO"
    log "INFO" "Deployment log: ${LOG_FILE}"

    check_prerequisites
    deploy_core_infrastructure
    deploy_keycloak
    deploy_oauth2_proxy
    deploy_applications
    deploy_gitlab_runner
    enhance_health_monitor
    perform_health_checks
    display_access_info

    log "INFO" "Deployment completed successfully!"
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
