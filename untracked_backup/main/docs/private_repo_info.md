# Private Repository Information

This document outlines which files and configurations should be maintained in the private repository for security purposes.

## Files to Move to Private Repository

### Deployment Scripts

- `scripts/deploy.sh` and variations
- Any scripts containing secrets or sensitive operations
- Custom deployment configurations

### Environment Files

- `.env` files containing actual values
- Environment-specific configurations
- Secret management scripts

### Access Configuration

- SSH key configurations
- Kubeconfig files
- Service account tokens
- API keys and secrets

### Security Configurations

- Certificate files
- Private keys
- Authentication tokens
- Security-related override files

### Infrastructure Details

- Detailed network configurations
- IP addresses and ports
- Internal service endpoints
- Infrastructure access patterns

## Repository Structure in Private Repo

```
private-homelab-infra/
├── .env                     # Main environment file
├── configs/
│   ├── production/         # Production-specific configurations
│   └── staging/           # Staging-specific configurations
├── scripts/
│   ├── deploy.sh          # Main deployment script
│   └── secrets/           # Secret management scripts
└── security/
    ├── certificates/      # SSL/TLS certificates
    └── keys/             # Private keys and tokens
```

## Usage Guidelines

1. Never commit sensitive files to the public repository
2. Keep the private repository access limited to essential personnel
3. Regularly audit access and credentials
4. Use environment templates in the public repo
5. Document but don't expose actual configurations

## Deployment Process

1. Clone both repositories
2. Copy necessary files from private to public repo's ignored directories
3. Use deployment scripts from private repo
4. Keep sensitive logs in private repo

## Backup Considerations

- Regular backups of private repository
- Encrypted backup storage
- Access log retention
- Backup restoration testing
