# Environment Variables

This document describes the environment variables used in the homelab infrastructure deployment.

## Required Variables

### Authentication

- `GRAFANA_ADMIN_PASSWORD`: Admin password for Grafana dashboard
  - Required in all environments
  - Must be at least 8 characters
  - Development has a default fallback of "devadmin" (not secure for production)

## Optional Variables

### Storage Configuration

- `PROMETHEUS_STORAGE_SIZE`: Storage size for Prometheus (default varies by environment)
  - Development: 10Gi
  - Staging: 20Gi
  - Production: 50Gi
- `LOKI_STORAGE_SIZE`: Storage size for Loki (default varies by environment)
  - Development: 5Gi
  - Staging: 10Gi
  - Production: 20Gi
- `GRAFANA_STORAGE_SIZE`: Storage size for Grafana (default varies by environment)
  - Development: 2Gi
  - Staging: 5Gi
  - Production: 10Gi

### Monitoring Configuration

- `PROMETHEUS_RETENTION_DAYS`: Days to retain Prometheus metrics
  - Development: 7d
  - Staging: 14d
  - Production: 30d

### Longhorn Settings

- `LONGHORN_REPLICA_COUNT`: Number of replicas for Longhorn volumes
  - Development: 1
  - Staging: 2
  - Production: 3
- `LONGHORN_BACKUP_TARGET`: S3 or NFS backup target (optional)
- `LONGHORN_BACKUP_SECRET`: Secret for backup target authentication (optional)

### General Settings

- `ENVIRONMENT`: Current deployment environment
  - Valid values: development, staging, production
  - Affects default values and feature flags
- `DEBUG`: Enable debug logging and features
  - Default: false
  - Set to true only in development

## Usage

1. Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

2. Update the values in `.env`:

   ```bash
   # Required
   GRAFANA_ADMIN_PASSWORD=your-secure-password

   # Optional - override defaults
   PROMETHEUS_RETENTION_DAYS=45
   LONGHORN_REPLICA_COUNT=2
   ```

3. Deploy with environment variables:

   ```bash
   # Development
   ./scripts/deploy.sh -e development

   # Production
   ./scripts/deploy.sh -e production
   ```

## Security Notes

- Never commit `.env` files to version control
- Use different passwords for each environment
- In production, all passwords should be randomly generated
- Consider using a secret management solution for production
