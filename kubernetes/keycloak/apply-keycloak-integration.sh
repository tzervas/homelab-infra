#!/bin/bash

# Script to apply Keycloak integration for all services
set -e

echo "Applying Keycloak client configurations..."

# Create directory if it doesn't exist
mkdir -p /tmp/keycloak-setup

# Apply Keycloak client configurations
echo "1. Applying Keycloak client configurations..."
kubectl apply -f keycloak-clients-config.yaml

# Update Grafana with Keycloak integration
echo "2. Updating Grafana with Keycloak integration..."
kubectl apply -f grafana-keycloak.yaml

# Update GitLab with Keycloak integration
echo "3. Updating GitLab with Keycloak integration..."
kubectl apply -f gitlab-keycloak.yaml

# Update OpenWebUI with Keycloak integration
echo "4. Updating OpenWebUI with Keycloak integration..."
kubectl apply -f ollama-webui-keycloak.yaml

# Deploy JupyterHub with Keycloak integration
echo "5. Deploying JupyterHub with Keycloak integration..."
kubectl apply -f jupyterhub-keycloak.yaml

# Deploy OAuth2 Proxy for Prometheus
echo "6. Deploying OAuth2 Proxy for Prometheus..."
kubectl apply -f oauth2-proxy-multi-client.yaml

# Wait for deployments to be ready
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=600s deployment/grafana -n monitoring
kubectl wait --for=condition=available --timeout=600s deployment/gitlab -n gitlab
kubectl wait --for=condition=available --timeout=600s deployment/open-webui -n ai-tools
kubectl wait --for=condition=available --timeout=600s deployment/jupyterhub -n jupyter
kubectl wait --for=condition=available --timeout=600s deployment/prometheus-oauth2-proxy -n oauth2-proxy

echo "All services have been configured with Keycloak authentication!"
echo ""
echo "Service URLs:"
echo "- Grafana: https://grafana.homelab.local"
echo "- GitLab: https://gitlab.homelab.local"
echo "- Prometheus: https://prometheus.homelab.local"
echo "- Ollama WebUI: https://ollama.homelab.local"
echo "- JupyterHub: https://jupyter.homelab.local"
echo ""
echo "Keycloak Admin: https://auth.homelab.local"
echo ""
echo "Default users:"
echo "- admin/homelab123! (admin access to all services)"
echo "- tzervas/tzervas123! (developer access)"
echo "- user/user123! (basic user access)"
