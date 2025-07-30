# Homelab Portal Enhancement Plan

## Overview

Enhance the existing homelab portal at `homelab.local` to include a comprehensive security dashboard and improve service management capabilities.

## Objectives

1. Update the landing page with dynamic service status indicators
2. Create a dedicated security dashboard for cluster security management
3. Integrate with existing authentication (OAuth2 Proxy + Keycloak)
4. Follow established development standards and best practices

## Development Plan

### Phase 1: Infrastructure Setup

1. Create a new branch for portal enhancements
2. Set up the homelab-portal namespace and resources
3. Create a Python-based backend service for dynamic status checks
4. Implement security metrics collection

### Phase 2: Backend Development

1. Create a FastAPI application for:
   - Service health status API
   - Security metrics aggregation
   - Authentication status monitoring
2. Integrate with Prometheus for metrics
3. Add Kubernetes API integration for cluster status

### Phase 3: Frontend Enhancement

1. Convert static HTML to a dynamic application
2. Add real-time service status updates
3. Create security dashboard components
4. Implement responsive design

### Phase 4: Security Dashboard

1. Create dedicated security views:
   - Authentication logs and patterns
   - Certificate status and expiration
   - Network policy compliance
   - Pod security standards compliance
   - RBAC audit trail
2. Integrate with Grafana for advanced visualizations

### Phase 5: Testing and Deployment

1. Unit tests for backend services
2. Integration tests with Kubernetes
3. Security validation
4. Deployment scripts and documentation

## Technical Stack

- Backend: Python 3.12+ with FastAPI
- Frontend: Modern HTML5/CSS3/JavaScript (vanilla for simplicity)
- Monitoring: Prometheus + Grafana integration
- Authentication: OAuth2 Proxy + Keycloak
- Deployment: Kubernetes manifests with Helm charts

## Directory Structure

```
kubernetes/homelab-portal/
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   ├── services/
│   │   └── models/
│   └── tests/
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── templates/
├── manifests/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
└── helm/
    └── homelab-portal/
        ├── Chart.yaml
        ├── values.yaml
        └── templates/

```

## Security Considerations

1. All endpoints require authentication via OAuth2 Proxy
2. RBAC policies for service account access
3. Network policies to restrict traffic
4. TLS encryption for all communications
5. Security headers in responses

## Success Criteria

1. Portal accessible at <https://homelab.local>
2. All services show real-time status
3. Security dashboard provides actionable insights
4. Performance: Page load < 2 seconds
5. 100% test coverage for critical paths
