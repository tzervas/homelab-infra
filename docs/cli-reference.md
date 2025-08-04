# CLI Reference

Complete command-line interface reference for the Homelab Infrastructure Orchestrator v0.9.0-beta.

## Global Options

Available for all commands:

```bash
python -m homelab_orchestrator [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

### Global Options

| Option | Default | Description |
|--------|---------|-------------|
| `--log-level` | `INFO` | Set logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `--environment` | `development` | Target environment: `development`, `staging`, `production` |
| `--cluster-type` | `local` | Cluster deployment type: `local`, `remote`, `hybrid` |
| `--project-root` | Current directory | Project root directory path |
| `--version` | - | Show version and exit |
| `--help` | - | Show help message |

### Examples

```bash
# Debug mode with production environment
python -m homelab_orchestrator --log-level DEBUG --environment production status

# Remote cluster deployment
python -m homelab_orchestrator --cluster-type remote deploy infrastructure

# Custom project root
python -m homelab_orchestrator --project-root /path/to/project config validate
```

## Main Commands

### deploy

Infrastructure and service deployment operations.

```bash
python -m homelab_orchestrator deploy SUBCOMMAND [OPTIONS]
```

#### deploy infrastructure

Deploy complete homelab infrastructure.

```bash
python -m homelab_orchestrator deploy infrastructure [OPTIONS]
```

**Options:**
- `--components TEXT`: Specific components to deploy (multiple allowed)
- `--dry-run`: Perform validation without deployment
- `--skip-hooks`: Skip deployment hooks

**Examples:**
```bash
# Deploy all infrastructure
python -m homelab_orchestrator deploy infrastructure

# Deploy specific components
python -m homelab_orchestrator deploy infrastructure --components metallb cert_manager

# Dry run deployment
python -m homelab_orchestrator deploy infrastructure --dry-run

# Production deployment without hooks
python -m homelab_orchestrator --environment production deploy infrastructure --skip-hooks
```

**Available Components:**
- `metallb`: MetalLB load balancer
- `cert_manager`: Certificate management
- `ingress_nginx`: NGINX ingress controller
- `keycloak`: Authentication server
- `monitoring`: Prometheus + Grafana
- `gitlab`: GitLab DevOps platform
- `ai_tools`: Ollama + OpenWebUI
- `jupyter`: JupyterLab
- `longhorn`: Distributed storage

#### deploy service

Deploy specific service.

```bash
python -m homelab_orchestrator deploy service SERVICE_NAME [OPTIONS]
```

**Options:**
- `--namespace TEXT`: Target namespace
- `--dry-run`: Validate without deployment

**Examples:**
```bash
# Deploy Grafana service
python -m homelab_orchestrator deploy service grafana

# Deploy to specific namespace
python -m homelab_orchestrator deploy service prometheus --namespace monitoring

# Dry run service deployment
python -m homelab_orchestrator deploy service keycloak --dry-run
```

### certificates

Certificate management operations.

```bash
python -m homelab_orchestrator certificates SUBCOMMAND [OPTIONS]
```

#### certificates deploy

Deploy cert-manager and certificate issuers.

```bash
python -m homelab_orchestrator certificates deploy
```

**Examples:**
```bash
# Deploy cert-manager with all issuers
python -m homelab_orchestrator certificates deploy

# Deploy in production environment
python -m homelab_orchestrator --environment production certificates deploy
```

#### certificates validate

Validate TLS certificates and endpoints.

```bash
python -m homelab_orchestrator certificates validate [OPTIONS]
```

**Options:**
- `--format [table|json]`: Output format (default: table)

**Examples:**
```bash
# Validate certificates (table format)
python -m homelab_orchestrator certificates validate

# JSON output for automation
python -m homelab_orchestrator certificates validate --format json
```

#### certificates check-expiry

Check certificate expiry dates.

```bash
python -m homelab_orchestrator certificates check-expiry [OPTIONS]
```

**Options:**
- `--format [table|json]`: Output format (default: table)

**Examples:**
```bash
# Check certificate expiry
python -m homelab_orchestrator certificates check-expiry

# JSON output with expiry details
python -m homelab_orchestrator certificates check-expiry --format json
```

#### certificates renew

Force renewal of a specific certificate.

```bash
python -m homelab_orchestrator certificates renew CERT_NAME [OPTIONS]
```

**Options:**
- `--namespace TEXT`: Certificate namespace (default: default)

**Examples:**
```bash
# Renew wildcard certificate
python -m homelab_orchestrator certificates renew homelab-wildcard-tls

# Renew certificate in specific namespace
python -m homelab_orchestrator certificates renew grafana-tls --namespace monitoring
```

### config

Configuration management.

```bash
python -m homelab_orchestrator config SUBCOMMAND [OPTIONS]
```

#### config validate

Validate configuration files.

```bash
python -m homelab_orchestrator config validate [OPTIONS]
```

**Options:**
- `--comprehensive`: Run comprehensive validation

**Examples:**
```bash
# Basic configuration validation
python -m homelab_orchestrator config validate

# Comprehensive validation
python -m homelab_orchestrator config validate --comprehensive

# Validate production configuration
python -m homelab_orchestrator --environment production config validate
```

#### config show

Show configuration values.

```bash
python -m homelab_orchestrator config show [CONFIG_TYPE] [OPTIONS]
```

**Arguments:**
- `CONFIG_TYPE`: Specific configuration section (optional)

**Options:**
- `--key TEXT`: Specific configuration key
- `--format [yaml|json]`: Output format (default: yaml)

**Examples:**
```bash
# Show all configuration
python -m homelab_orchestrator config show

# Show networking configuration
python -m homelab_orchestrator config show networking

# Show specific key in JSON format
python -m homelab_orchestrator config show services --key discovery --format json
```

### health

Health monitoring and validation.

```bash
python -m homelab_orchestrator health SUBCOMMAND [OPTIONS]
```

#### health check

Check system health status.

```bash
python -m homelab_orchestrator health check [OPTIONS]
```

**Options:**
- `--comprehensive`: Run comprehensive health check
- `--component TEXT`: Check specific components (multiple allowed)
- `--format [table|json]`: Output format (default: table)

**Examples:**
```bash
# Basic health check
python -m homelab_orchestrator health check

# Comprehensive health check
python -m homelab_orchestrator health check --comprehensive

# Check specific components
python -m homelab_orchestrator health check --component prometheus --component grafana

# JSON output for monitoring
python -m homelab_orchestrator health check --format json
```

#### health monitor

Start continuous health monitoring.

```bash
python -m homelab_orchestrator health monitor [OPTIONS]
```

**Options:**
- `--interval INTEGER`: Monitoring interval in seconds (default: 60)
- `--duration INTEGER`: Monitoring duration in seconds (0 for continuous, default: 0)

**Examples:**
```bash
# Start continuous monitoring
python -m homelab_orchestrator health monitor

# Monitor for 1 hour with 30-second intervals
python -m homelab_orchestrator health monitor --interval 30 --duration 3600
```

### manage

Backup, teardown, and recovery operations.

```bash
python -m homelab_orchestrator manage SUBCOMMAND [OPTIONS]
```

#### manage backup

Backup infrastructure components.

```bash
python -m homelab_orchestrator manage backup [OPTIONS]
```

**Options:**
- `--components TEXT`: Specific components to backup (multiple allowed)

**Examples:**
```bash
# Backup all components
python -m homelab_orchestrator manage backup

# Backup specific components
python -m homelab_orchestrator manage backup --components prometheus --components grafana
```

#### manage teardown

Teardown complete infrastructure.

```bash
python -m homelab_orchestrator manage teardown [OPTIONS]
```

**Options:**
- `--force`: Force teardown without confirmation
- `--no-backup`: Skip backup before teardown

**Examples:**
```bash
# Teardown with confirmation and backup
python -m homelab_orchestrator manage teardown

# Force teardown without backup
python -m homelab_orchestrator manage teardown --force --no-backup
```

#### manage recover

Recover infrastructure components from backup.

```bash
python -m homelab_orchestrator manage recover [OPTIONS]
```

**Options:**
- `--components TEXT`: Specific components to recover (multiple allowed)

**Examples:**
```bash
# Recover all components
python -m homelab_orchestrator manage recover

# Recover specific components
python -m homelab_orchestrator manage recover --components monitoring
```

### gpu

GPU resource management.

```bash
python -m homelab_orchestrator gpu SUBCOMMAND [OPTIONS]
```

#### gpu discover

Discover available GPU resources.

```bash
python -m homelab_orchestrator gpu discover [OPTIONS]
```

**Options:**
- `--format [table|json]`: Output format (default: table)

**Examples:**
```bash
# Discover GPUs (table format)
python -m homelab_orchestrator gpu discover

# JSON output for automation
python -m homelab_orchestrator gpu discover --format json
```

#### gpu status

Show GPU resource status.

```bash
python -m homelab_orchestrator gpu status [OPTIONS]
```

**Options:**
- `--format [table|json]`: Output format (default: table)

**Examples:**
```bash
# Show GPU status
python -m homelab_orchestrator gpu status

# JSON output
python -m homelab_orchestrator gpu status --format json
```

### webhook

Webhook management.

```bash
python -m homelab_orchestrator webhook SUBCOMMAND [OPTIONS]
```

#### webhook start

Start webhook server.

```bash
python -m homelab_orchestrator webhook start [OPTIONS]
```

**Options:**
- `--host TEXT`: Host to bind to (default: 0.0.0.0)
- `--port INTEGER`: Port to bind to (default: 8080)

**Examples:**
```bash
# Start webhook server on default port
python -m homelab_orchestrator webhook start

# Start on specific host and port
python -m homelab_orchestrator webhook start --host 127.0.0.1 --port 9000
```

### status

Show overall system status.

```bash
python -m homelab_orchestrator status [OPTIONS]
```

**Options:**
- `--format [table|json]`: Output format (default: table)

**Examples:**
```bash
# Show system status
python -m homelab_orchestrator status

# JSON output for monitoring
python -m homelab_orchestrator status --format json
```

## Output Formats

Most commands support multiple output formats:

### Table Format (Default)

Human-readable table format:

```bash
python -m homelab_orchestrator certificates check-expiry
```

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                      Certificate Expiry Information                                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Certificate            │ Namespace │ Days Until Expiry │ Status │ Needs Renewal │
├────────────────────────┼───────────┼───────────────────┼────────┼───────────────┤
│ homelab-wildcard-tls   │ default   │ 60                │ ready  │ ✅ NO          │
│ grafana-tls           │ monitoring │ 15                │ ready  │ ⚠️ YES         │
└────────────────────────┴───────────┴───────────────────┴────────┴───────────────┘
```

### JSON Format

Machine-readable JSON format:

```bash
python -m homelab_orchestrator certificates check-expiry --format json
```

```json
{
  "status": "success",
  "certificates": [
    {
      "name": "homelab-wildcard-tls",
      "namespace": "default",
      "days_until_expiry": 60,
      "status": "ready",
      "needs_renewal": false
    }
  ]
}
```

## Environment Integration

### Shell Completion

Enable shell autocompletion:

```bash
# Bash
eval "$(_HOMELAB_ORCHESTRATOR_COMPLETE=bash_source homelab-orchestrator)"

# Zsh  
eval "$(_HOMELAB_ORCHESTRATOR_COMPLETE=zsh_source homelab-orchestrator)"

# Fish
eval (homelab-orchestrator --help)  # Fish autocompletion
```

### Environment Variables

Control CLI behavior with environment variables:

```bash
# Set default log level
export HOMELAB_LOG_LEVEL=DEBUG

# Set default environment
export HOMELAB_ENVIRONMENT=production

# Set project root
export HOMELAB_PROJECT_ROOT=/path/to/project

# Use variables
python -m homelab_orchestrator status  # Uses DEBUG log level and production environment
```

### Configuration Files

CLI respects configuration files:

- `.env`: Environment variables and secrets
- `config/consolidated/`: Configuration files
- `~/.homelab/config.yaml`: User-specific configuration

## Exit Codes

The CLI uses standard exit codes:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Misuse of shell command |
| 130 | Script terminated by Control-C |

**Examples:**
```bash
# Check exit code
python -m homelab_orchestrator config validate
echo $?  # 0 for success, 1 for failure

# Use in scripts
if python -m homelab_orchestrator certificates validate; then
    echo "Certificates are valid"
else
    echo "Certificate validation failed"
    exit 1
fi
```

## Common Usage Patterns

### Deployment Workflow

```bash
# 1. Validate configuration
python -m homelab_orchestrator config validate

# 2. Deploy certificates
python -m homelab_orchestrator certificates deploy

# 3. Deploy infrastructure (dry-run first)
python -m homelab_orchestrator deploy infrastructure --dry-run

# 4. Deploy for real
python -m homelab_orchestrator deploy infrastructure

# 5. Validate deployment
python -m homelab_orchestrator certificates validate
python -m homelab_orchestrator health check --comprehensive
```

### Monitoring Workflow

```bash
# Check system status
python -m homelab_orchestrator status

# Check certificate expiry
python -m homelab_orchestrator certificates check-expiry

# Run health checks
python -m homelab_orchestrator health check

# Start continuous monitoring
python -m homelab_orchestrator health monitor --interval 300  # Every 5 minutes
```

### Troubleshooting Workflow

```bash
# Enable debug logging
python -m homelab_orchestrator --log-level DEBUG status

# Validate configuration
python -m homelab_orchestrator config validate --comprehensive

# Check specific component
python -m homelab_orchestrator health check --component prometheus

# Force certificate renewal
python -m homelab_orchestrator certificates renew homelab-wildcard-tls
```

## Scripting and Automation

### Bash Integration

```bash
#!/bin/bash
set -euo pipefail

# Function to deploy with retry
deploy_with_retry() {
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo "Deployment attempt $attempt/$max_attempts"
        
        if python -m homelab_orchestrator deploy infrastructure --components "$1"; then
            echo "Deployment successful"
            return 0
        fi
        
        echo "Deployment failed, retrying in 30 seconds..."
        sleep 30
        ((attempt++))
    done
    
    echo "Deployment failed after $max_attempts attempts"
    return 1
}

# Use the function
deploy_with_retry "metallb"
```

### JSON Processing

```bash
# Get certificate expiry in days
EXPIRY_DAYS=$(python -m homelab_orchestrator certificates check-expiry --format json | \
    jq -r '.certificates[] | select(.name == "homelab-wildcard-tls") | .days_until_expiry')

if [ "$EXPIRY_DAYS" -lt 30 ]; then
    echo "Certificate expires in $EXPIRY_DAYS days, renewing..."
    python -m homelab_orchestrator certificates renew homelab-wildcard-tls
fi
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Deploy Infrastructure
  run: |
    python -m homelab_orchestrator config validate
    python -m homelab_orchestrator deploy infrastructure --dry-run
    python -m homelab_orchestrator deploy infrastructure
    
- name: Validate Deployment
  run: |
    python -m homelab_orchestrator health check --comprehensive --format json > health-report.json
    python -m homelab_orchestrator certificates validate --format json > cert-report.json
```

## Tips and Best Practices

### Performance Tips

1. **Use specific components**: `--components metallb` is faster than deploying everything
2. **Dry-run first**: Always test with `--dry-run` before actual deployment
3. **JSON for automation**: Use `--format json` for scripting and monitoring
4. **Debug selectively**: Use `--log-level DEBUG` only when troubleshooting

### Security Tips

1. **Environment separation**: Use `--environment` to separate dev/staging/prod
2. **Validate configuration**: Always run `config validate` before deployment
3. **Monitor certificates**: Set up automated certificate expiry checking
4. **Use comprehensive health checks**: Run `health check --comprehensive` regularly

### Troubleshooting Tips

1. **Check status first**: Run `status` to get overall system health
2. **Enable debug logging**: Use `--log-level DEBUG` for detailed information
3. **Validate step by step**: Check config, then certificates, then health
4. **Use dry-run**: Test deployments with `--dry-run` to identify issues

---

**💡 Pro Tip**: Use `python -m homelab_orchestrator COMMAND --help` to get detailed help for any specific command!