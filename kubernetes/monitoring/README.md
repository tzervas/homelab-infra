# Monitoring Stack

This directory contains the monitoring and observability configuration for the homelab infrastructure.

## Components

### Prometheus Stack

- **Prometheus Operator**: Manages Prometheus instances and configuration
- **Prometheus**: Metrics collection and storage
- **AlertManager**: Alert routing and notifications
- **Grafana**: Visualization and dashboards

### Logging Stack

- **Loki**: Log aggregation and storage
- **Promtail**: Log collection agent
- **Grafana**: Log visualization

### Service Monitoring

- **ServiceMonitors**: Application-specific metrics collection
- **PodMonitors**: Pod-level metrics collection
- **PrometheusRules**: Recording and alerting rules

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Monitoring Stack                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Grafana    │  │  Prometheus  │  │ AlertManager │         │
│  │ (Dashboard)  │  │ (Metrics)    │  │ (Alerting)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │     Loki     │  │   Promtail   │  │ Node Exporter│         │
│  │  (Logs)      │  │ (Collection) │  │ (Node Metrics│         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Application Layer                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    GitLab    │  │   Keycloak   │  │  Kubernetes  │         │
│  │              │  │              │  │   Cluster    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment

1. **Deploy Prometheus Operator**

```bash
kubectl apply -f prometheus/prometheus-operator.yaml
```

2. **Deploy Grafana**

```bash
kubectl apply -f grafana/grafana.yaml
```

3. **Deploy AlertManager**

```bash
kubectl apply -f alerting/alertmanager.yaml
```

4. **Apply ServiceMonitors**

```bash
kubectl apply -f service-monitors/
```

## Configuration

### Prometheus Configuration

- Scrape intervals and retention policies
- Service discovery for Kubernetes components
- Recording rules for performance optimization

### Grafana Configuration

- Data source configuration for Prometheus and Loki
- Dashboard provisioning
- User authentication and authorization

### AlertManager Configuration

- Routing rules for different alert types
- Notification channels (email, Slack, etc.)
- Silence and inhibition rules

## Dashboards

### Infrastructure Dashboards

- Kubernetes cluster overview
- Node resource utilization
- Pod resource consumption
- Network traffic and performance

### Application Dashboards

- GitLab performance metrics
- Keycloak authentication metrics
- Application response times
- Error rates and availability

### Custom Dashboards

- Business metrics
- SLA monitoring
- Capacity planning
- Security monitoring

## Alerting

### Infrastructure Alerts

- Node resource exhaustion
- Pod restart loops
- Storage space warnings
- Network connectivity issues

### Application Alerts

- Service availability
- Response time degradation
- Error rate increases
- Authentication failures

### Custom Alerts

- Business metric thresholds
- Security events
- Backup failures
- Certificate expiration

## Maintenance

### Regular Tasks

- Review and update alerting rules
- Optimize dashboard performance
- Clean up old metrics data
- Update monitoring components

### Troubleshooting

- Common monitoring issues
- Performance optimization
- Data retention management
- Dashboard troubleshooting

This monitoring stack provides comprehensive observability for the homelab infrastructure with alerting and visualization capabilities.
