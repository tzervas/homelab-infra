# Secure Command Execution Standards

This document outlines the security standards and best practices for executing shell commands within the homelab infrastructure projects.

## Core Principles

1. **Principle of Least Privilege**
   - Execute commands with minimal required permissions
   - Use specific service accounts where possible
   - Avoid running commands as root unless absolutely necessary

2. **Input Validation**
   - All command parameters must be validated before execution
   - Use allowlists for permitted commands
   - Sanitize and escape all user-provided input

3. **Shell Injection Prevention**
   - Never use shell=True with subprocess
   - Use subprocess.run with command lists instead of strings
   - Properly escape all command arguments using shlex

4. **Error Handling**
   - Implement comprehensive error handling for all command executions
   - Log all command failures with appropriate context
   - Fail safely when commands error

5. **Logging and Auditing**
   - Log all command execution attempts
   - Include command parameters, timestamps, and execution context
   - Maintain audit trails for security-sensitive operations

## Implementation Standards

### 1. Command Execution

Always use the `command_utils.execute_command()` function for executing shell commands:

```python
from homelab_orchestrator.utils.command_utils import execute_command

# Good - Use list format and no shell=True
returncode, stdout, stderr = execute_command(
    ["kubectl", "get", "pods", "-n", namespace],
    allowed_commands=["kubectl"]
)

# Bad - Don't use string format or shell=True
subprocess.run(f"kubectl get pods -n {namespace}", shell=True)  # INSECURE
```

### 2. Input Validation

Always validate command inputs:

```python
# Good - Validate command against allowed list
allowed_commands = ["kubectl", "helm", "k3s"]
if not validate_command(command, allowed_commands):
    raise ValueError("Invalid command")

# Bad - Direct command execution without validation
os.system(user_input)  # INSECURE
```

### 3. Error Handling

Implement proper error handling:

```python
try:
    returncode, stdout, stderr = execute_command(command)
except subprocess.CalledProcessError as e:
    logger.error(f"Command failed: {e}")
    # Handle error appropriately
except subprocess.TimeoutExpired as e:
    logger.error(f"Command timed out: {e}")
    # Handle timeout
```

### 4. Logging

Ensure comprehensive logging:

```python
# Good - Log command execution with context
logger.info(f"Executing command in {context}")
returncode, stdout, stderr = execute_command(command)
logger.info(f"Command completed with code {returncode}")

# Bad - No logging or insufficient context
subprocess.run(command)  # INSECURE - No logging
```

## Security Considerations

### Command Injection Prevention

1. **Never** use string concatenation for commands:
   ```python
   # Bad
   cmd = f"kubectl delete pod {pod_name}"  # INSECURE
   
   # Good
   cmd = ["kubectl", "delete", "pod", pod_name]
   ```

2. **Always** use argument lists:
   ```python
   # Bad
   subprocess.run(f"git clone {repo_url}", shell=True)  # INSECURE
   
   # Good
   execute_command(["git", "clone", repo_url])
   ```

### Sensitive Data Handling

1. Never expose sensitive data in command arguments:
   ```python
   # Bad
   execute_command(f"curl -H 'Authorization: {api_key}' {url}")  # INSECURE
   
   # Good
   env = {"API_KEY": api_key}
   execute_command(["curl", "-H", f"Authorization: ${API_KEY}", url], env=env)
   ```

2. Use environment variables for secrets:
   ```python
   # Good
   env = os.environ.copy()
   env["KUBECONFIG"] = kubeconfig_path
   execute_command(["kubectl", "apply", "-f", manifest], env=env)
   ```

## Monitoring and Auditing

### Logging Standards

1. **Command Execution Logging**
   - Log all command attempts
   - Include command context and parameters
   - Log execution results and errors

2. **Audit Trail**
   - Maintain detailed audit logs for security-sensitive operations
   - Include timestamps and execution context
   - Regular log rotation and archival

### Security Monitoring

1. **Failed Command Monitoring**
   - Monitor for repeated command failures
   - Alert on suspicious patterns
   - Regular security audit reviews

2. **Access Control Monitoring**
   - Track privileged command usage
   - Monitor sudo escalations
   - Regular access pattern reviews

## Testing and Validation

### Security Testing

1. **Command Injection Testing**
   - Regular security testing for command injection vulnerabilities
   - Automated testing with security test cases
   - Penetration testing for command execution paths

2. **Input Validation Testing**
   - Test boundary cases for command validation
   - Verify allowlist effectiveness
   - Test error handling paths

## Maintenance and Updates

1. **Regular Review**
   - Periodic review of command execution patterns
   - Update allowed command lists
   - Review and update security standards

2. **Security Patches**
   - Keep dependencies up to date
   - Apply security patches promptly
   - Regular security assessments

## References

1. [Python subprocess security](https://docs.python.org/3/library/subprocess.html#security-considerations)
2. [OWASP Command Injection Prevention](https://owasp.org/www-community/attacks/Command_Injection)
3. [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html)
