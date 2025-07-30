#!/bin/bash

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Homelab Portal Status Check ===${NC}\n"

# Get external IP
EXTERNAL_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "192.168.16.100")

echo -e "${GREEN}Portal Access Information:${NC}"
echo -e "External IP: ${EXTERNAL_IP}"
echo -e "URL: https://homelab.local"
echo -e "\nMake sure this line is in your /etc/hosts:"
echo -e "${EXTERNAL_IP} homelab.local"

echo -e "\n${GREEN}Service Status:${NC}"
echo "Portal Pods:"
kubectl get pods -n homelab-portal -o wide | grep enhanced-portal

echo -e "\nIngress Controller:"
kubectl get pods -n ingress-nginx | grep controller

echo -e "\nIngress Rules:"
kubectl get ingress --all-namespaces | grep homelab

echo -e "\n${GREEN}Resource Usage:${NC}"
kubectl top pods -n homelab-portal 2>/dev/null || echo "Metrics not available"

echo -e "\n${GREEN}Recent Events:${NC}"
kubectl get events -n homelab-portal --sort-by='.lastTimestamp' | tail -5

# Test connectivity
echo -e "\n${GREEN}Testing Connectivity:${NC}"
if curl -k -s -o /dev/null -w "%{http_code}" https://${EXTERNAL_IP} | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ Portal is accessible${NC}"
else
    echo -e "${RED}✗ Portal is not accessible${NC}"
fi

# Show logs if there are issues
if kubectl get pods -n homelab-portal | grep -v Running | grep -v NAME > /dev/null 2>&1; then
    echo -e "\n${YELLOW}Warning: Some pods are not running properly${NC}"
    kubectl get pods -n homelab-portal | grep -v Running | grep -v NAME
fi

echo -e "\n${BLUE}=== Check Complete ===${NC}"
