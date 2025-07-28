# Terraform Drift Resolution

## Symptom

- Alert: `TerraformStateDriftDetected`
- Configuration drift detected between Terraform state and actual infrastructure
- Resources may have been modified outside of Terraform

## Impact

- **Severity**: Warning
- **Impact**: Medium - Infrastructure may be in an inconsistent state
- **Urgency**: Medium - Should be resolved within 4 hours during business hours

## Investigation

### 1. Check Alert Details

```bash
# Check Prometheus for drift details
curl -s "http://prometheus.homelab.local:9090/api/v1/query?query=terraform_state_drift_detected" | jq .

# Check specific environment and workspace
kubectl get events -n monitoring --field-selector reason=TerraformDrift
```

### 2. Identify Affected Resources

```bash
# Navigate to the affected environment
cd terraform/environments/${ENVIRONMENT}

# Run terraform plan to see differences
terraform plan -detailed-exitcode

# Get specific resource details
terraform show -json | jq '.values.root_module.resources[] | select(.type == "RESOURCE_TYPE")'
```

### 3. Check Recent Changes

```bash
# Check recent commits that might have caused drift
git log --oneline -n 10 --grep="terraform"

# Check if anyone made manual changes
kubectl get events --sort-by=.metadata.creationTimestamp
```

## Resolution

### Option 1: Import Manual Changes (Recommended)

If the manual changes are desired and should be preserved:

```bash
# 1. Update Terraform configuration to match current state
# Edit the relevant .tf files to match the actual infrastructure

# 2. Run terraform plan to verify changes
terraform plan

# 3. Apply the updated configuration
terraform apply

# 4. Verify drift is resolved
terraform plan -detailed-exitcode
echo $?  # Should return 0 if no drift
```

### Option 2: Revert Manual Changes

If the manual changes should be reverted:

```bash
# 1. Run terraform apply to restore desired state
terraform apply -auto-approve

# 2. Verify resources match desired state
terraform plan -detailed-exitcode

# 3. Check affected services are functioning
kubectl get pods -A --field-selector=status.phase!=Running
```

### Option 3: Refresh State (Caution)

If state is out of sync but infrastructure is correct:

```bash
# 1. Backup current state
terraform show > state-backup-$(date +%Y%m%d-%H%M%S).json

# 2. Refresh state from current infrastructure
terraform refresh

# 3. Verify state matches infrastructure
terraform plan -detailed-exitcode
```

## Verification

### 1. Confirm Drift is Resolved

```bash
# Run terraform plan - should show no changes
terraform plan -detailed-exitcode
PLAN_EXIT_CODE=$?

if [ $PLAN_EXIT_CODE -eq 0 ]; then
    echo "✅ No drift detected"
elif [ $PLAN_EXIT_CODE -eq 2 ]; then
    echo "❌ Drift still present"
    terraform plan
else
    echo "⚠️  Terraform plan failed"
fi
```

### 2. Check Monitoring

```bash
# Verify drift metric is cleared
curl -s "http://prometheus.homelab.local:9090/api/v1/query?query=terraform_state_drift_detected{environment=\"${ENVIRONMENT}\"}" | jq .
```

### 3. Test Infrastructure

```bash
# Run basic connectivity tests
kubectl get nodes
kubectl get pods -A --field-selector=status.phase!=Running

# Test specific services affected by drift
curl -I https://grafana.homelab.local/api/health
```

## Prevention

### 1. Implement Drift Detection

```bash
# Add to CI/CD pipeline
#!/bin/bash
# drift-check.sh
terraform plan -detailed-exitcode
PLAN_EXIT_CODE=$?

if [ $PLAN_EXIT_CODE -eq 2 ]; then
    echo "Drift detected! Creating issue..."
    # Create GitHub issue or send notification
fi
```

### 2. Access Controls

- Review who has administrative access to infrastructure
- Implement approval processes for manual changes
- Use RBAC to limit direct cluster access

### 3. Monitoring and Alerting

```yaml
# Add to terraform-state-monitor configuration
drift_check:
  enabled: true
  schedule: "*/15 * * * *"  # Every 15 minutes
  notify_on_drift: true
  create_issues: true
```

### 4. Documentation

- Document all approved manual change procedures
- Update runbooks for emergency procedures
- Train team on proper change management

## Escalation

### Level 1 (Immediate)

- **When**: Drift affects critical production services
- **Action**: Page on-call engineer
- **Contact**: Slack #infrastructure-alerts

### Level 2 (2 hours)

- **When**: Unable to resolve drift or widespread impact
- **Action**: Escalate to infrastructure team lead
- **Contact**: <infrastructure-lead@homelab.local>

### Level 3 (4 hours)

- **When**: Potential data loss or security implications
- **Action**: Escalate to operations manager
- **Contact**: <ops-manager@homelab.local>

## Related Documentation

- [Terraform State Management](../infrastructure/terraform-state.md)
- [Change Management Process](../../processes/change-management.md)
- [Infrastructure Monitoring](../../monitoring/infrastructure.md)
- [Emergency Procedures](../../emergency/infrastructure.md)

## Change Log

- 2024-01-15: Initial runbook creation
- 2024-01-20: Added automated drift detection
- 2024-01-25: Updated escalation procedures
