# Homelab Infrastructure - Docker Compose Setup

This directory contains the Docker Compose configuration for the Homelab Infrastructure PoC/MVP phase.

## Quick Start

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Generate secure secrets:**
   ```bash
   # Generate OAuth2 secrets
   openssl rand -base64 32
   # Copy output to OAUTH2_CLIENT_SECRET and OAUTH2_COOKIE_SECRET in .env
   ```

3. **Start services:**
   ```bash
   docker-compose up -d
   ```

4. **Check status:**
   ```bash
   docker-compose ps
   docker-compose logs -f
   ```

## Services

### Core Services
- **PostgreSQL**: Database for Keycloak
- **Keycloak**: Authentication and identity management (port 8080)
- **OAuth2-Proxy**: Authentication proxy (port 4180)

### Monitoring Stack
- **Prometheus**: Metrics collection (port 9090)
- **Grafana**: Visualization dashboards (port 3000)
- **AlertManager**: Alert management (port 9093)

### Portal
- **Landing Page**: Service dashboard (port 8000)

## Access URLs

After starting services, access them at:
- Portal: http://localhost:8000
- Keycloak: http://localhost:8080
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- AlertManager: http://localhost:9093

## Configuration

### Environment Variables
All configuration is managed through the `.env` file. See `.env.example` for all available options.

### Service Configuration
- **Prometheus**: `config/prometheus/prometheus.yml`
- **Grafana**: `config/grafana/` (provisioning)
- **AlertManager**: `config/alertmanager/alertmanager.yml`
- **Portal**: `portal/index.html`

## Data Persistence

Data is persisted in Docker volumes:
- `homelab-postgres-data`: PostgreSQL database
- `homelab-prometheus-data`: Prometheus metrics
- `homelab-grafana-data`: Grafana dashboards and settings

## Management Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service-name]

# Restart a service
docker-compose restart [service-name]

# Update services
docker-compose pull
docker-compose up -d

# Clean up (WARNING: removes volumes)
docker-compose down -v
```

## Adding More Services

To add services like GitLab, JupyterLab, or Ollama, see the service-specific compose files in `services/` directory.

## Troubleshooting

### Services won't start
- Check Docker is running: `docker ps`
- Check logs: `docker-compose logs [service-name]`
- Verify `.env` file exists and has required values

### Can't access services
- Check services are running: `docker-compose ps`
- Verify ports aren't already in use
- Check firewall settings

### Database connection errors
- Ensure PostgreSQL is healthy: `docker-compose ps postgres`
- Check database credentials in `.env`
- Wait for database to fully initialize (first start takes longer)

## Next Steps

After basic services are running:
1. Configure Keycloak realm and clients
2. Set up Grafana dashboards
3. Configure OAuth2-Proxy for SSO
4. Deploy additional services (GitLab, Jupyter, Ollama)
