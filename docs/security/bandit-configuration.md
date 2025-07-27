# Bandit Security Scanning Configuration

## Overview

This document describes the bandit security scanning configuration for the homelab infrastructure project. Bandit is a tool designed to find common security issues in Python code.

## Configuration Locations

The bandit configuration is defined in multiple places:

1. **Primary Configuration**: `pyproject.toml` (under `[tool.bandit]` section)
2. **Alternative Configuration**: `.bandit` (INI format)
3. **Pre-commit Integration**: `.pre-commit-config.yaml`

## Configuration Details

### Excluded Directories

The following directories are excluded from security scanning:

- `tests/` - Test files often contain patterns that trigger false positives
- `untracked_backup/` - Backup files not part of the active codebase
- `.venv/`, `venv/` - Virtual environment directories
- `.git/` - Git repository metadata
- Cache directories: `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`
- Build artifacts: `build/`, `dist/`, `*.egg-info/`
- `examples/` - Example configurations may contain placeholder credentials
- `.trunk/` - Trunk tool configuration
- `docs/` - Documentation files

### Severity and Confidence Levels

- **Severity**: `LOW` - Reports all issues with low severity or higher
- **Confidence**: `LOW` - Reports all issues with low confidence or higher

This configuration ensures comprehensive security scanning while maintaining a manageable signal-to-noise ratio.

### Skipped Tests

The following bandit test IDs are skipped based on project requirements:

| Test ID | Name | Reason for Skipping |
|---------|------|-------------------|
| B101 | assert_used | Assertions are used for validation in the codebase |
| B601 | paramiko_calls | SSH operations may be required for infrastructure management |
| B104 | hardcoded_bind_all_interfaces | K3s/Kubernetes configurations legitimately bind to 0.0.0.0 |
| B108 | hardcoded_tmp_directory | Temporary directories are used in a controlled manner |
| B404 | import_subprocess | Subprocess module is required for system commands |
| B603 | subprocess_without_shell_equals_true | Controlled subprocess usage with proper input validation |
| B607 | start_process_with_partial_path | Acceptable for well-known system commands |

### Additional Configuration

#### Hardcoded Password Detection

The configuration includes patterns to detect potential hardcoded passwords:

- password
- passwd
- secret
- token
- secrete

Password checks are skipped for specific function calls like `requests.get`, `requests.post`, etc., where authentication parameters are expected.

#### Shell Injection Protection

The configuration monitors for potentially dangerous shell operations and subprocess calls, with appropriate exceptions for controlled usage patterns.

## Running Bandit

### Command Line

```bash
# Run bandit with pyproject.toml configuration
bandit -r scripts/

# Run with specific severity/confidence levels
bandit -r scripts/ -ll -i

# Generate JSON report
bandit -r scripts/ -f json -o bandit-report.json

# Run with INI configuration file
bandit --ini .bandit -r scripts/
```

### Pre-commit Hook

Bandit runs automatically as part of the pre-commit hooks:

```bash
# Install pre-commit hooks
uv tool install pre-commit
pre-commit install

# Run all hooks including bandit
pre-commit run --all-files

# Run only bandit
pre-commit run bandit --all-files
```

### Integration with CI/CD

Bandit is integrated into the CI/CD pipeline through pre-commit hooks and can also be run as a standalone step:

```yaml
# Example GitHub Actions step
- name: Run Bandit Security Scan
  run: |
    uv sync
    uv run bandit -r scripts/ -ll -i -f json -o bandit-report.json
```

## Suppressing False Positives

For specific lines where bandit reports false positives, use inline comments:

```python
# Suppress all bandit warnings for this line
subprocess.run(cmd, shell=True)  # nosec

# Suppress specific bandit test
subprocess.run(cmd, shell=True)  # nosec B602
```

## Best Practices

1. **Regular Updates**: Keep bandit updated to benefit from new security checks
2. **Review Reports**: Regularly review bandit reports and address findings
3. **Document Exceptions**: Document why specific tests are skipped
4. **Gradual Enhancement**: Start with low thresholds and gradually increase strictness
5. **Team Training**: Ensure team members understand security best practices

## Troubleshooting

### Common Issues

1. **Too Many False Positives**: Consider raising severity/confidence thresholds or adding specific test IDs to the skip list
2. **Missing Real Issues**: Lower the thresholds or remove tests from the skip list
3. **Performance Issues**: Use exclude patterns to skip unnecessary directories

### Getting Help

- Bandit Documentation: <https://bandit.readthedocs.io/>
- Issue Tracker: <https://github.com/PyCQA/bandit/issues>
- Security Best Practices: <https://python.readthedocs.io/en/latest/library/security_warnings.html>
