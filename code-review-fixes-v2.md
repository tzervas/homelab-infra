# Code Review Fixes for Testing Framework - Round 2

Please implement the following fixes for the code review comments. DO NOT create any commits - just make the code changes.

## Overall Improvements

### 1. Centralize Logging and Import Logic
Create a new file `scripts/testing/common.py` with:
- Shared logger configuration function that all modules can import
- Common import fallback logic for optional dependencies
- This will reduce boilerplate across all modules

### 2. Extract Configuration
Create a new file `scripts/testing/config.py` or `scripts/testing/default_config.yaml` with:
- Service endpoints (currently hardcoded in integration_tester.py)
- Timeouts (short_timeout, long_timeout)
- Service definitions from service_checker.py
- Allow CLI parameters to override these defaults

### 3. Consolidate Test Result Rendering
The test_reporter.py already exists but needs to be extended to:
- Handle all result rendering (console, JSON, Markdown)
- Be imported and used by other modules instead of them implementing their own rendering

## Individual Fixes

### Fix 1: Authentication Token in `integration_tester.py:529`
Change the get_auth_token method to raise NotImplementedError:
```python
def get_auth_token(self, endpoint: ServiceEndpoint) -> Optional[str]:
    """Get authentication token for the endpoint.
    
    Override this method to provide actual authentication logic.
    """
    raise NotImplementedError(
        "Authentication required but get_auth_token() not implemented. "
        "Override this method or set auth tokens via environment variables."
    )
```

### Fix 2: CPU Parsing in `service_checker.py:314`
Enhance the _parse_cpu method to handle all Kubernetes formats including scientific notation:
```python
def _parse_cpu(self, cpu_str: str) -> int:
    """Parse CPU string to millicores.
    
    Supports all Kubernetes CPU formats:
    - '100m' (millicores)
    - '0.5', '1.5' (cores as float)
    - '1e3m', '1e-3' (scientific notation)
    - '250u' (250 microcores = 0.25m)
    - '500n' (500 nanocores = 0.0005m)
    """
    try:
        from kubernetes.utils.quantity import parse_quantity
        # parse_quantity returns the value in base units
        # For CPU, base unit is "core" so we convert to millicores
        cores = parse_quantity(cpu_str)
        return int(cores * 1000)
    except ImportError:
        # Fallback implementation
        cpu_str = cpu_str.strip()
        try:
            # Handle scientific notation
            if 'e' in cpu_str.lower():
                if cpu_str.endswith('m'):
                    return int(float(cpu_str[:-1]))
                else:
                    return int(float(cpu_str) * 1000)
            
            # Handle units
            if cpu_str.endswith('m'):
                return int(float(cpu_str[:-1]))
            elif cpu_str.endswith('u'):  # microcores
                return int(float(cpu_str[:-1]) / 1000)
            elif cpu_str.endswith('n'):  # nanocores
                return int(float(cpu_str[:-1]) / 1_000_000)
            else:
                # Assume cores (can be float)
                return int(float(cpu_str) * 1000)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid CPU string format: '{cpu_str}'") from e
```

### Fix 3: Memory Parsing in `service_checker.py:337`
The memory parsing already uses parse_quantity but the fallback needs enhancement:
```python
def _parse_memory(self, memory_str: str) -> int:
    """Parse memory string to Mi (Mebibytes).
    
    Supports all Kubernetes memory formats including:
    - Binary: Ki, Mi, Gi, Ti, Pi, Ei
    - Decimal: k, K, M, G, T, P, E
    - Plain bytes
    """
    try:
        from kubernetes.utils.quantity import parse_quantity
        # parse_quantity returns bytes
        bytes_value = parse_quantity(memory_str)
        return int(bytes_value / (1024 * 1024))  # Convert to MiB
    except ImportError:
        # Enhanced fallback implementation
        memory_str = memory_str.strip()
        
        # Binary units (powers of 1024)
        binary_units = {
            'Ki': 1024,
            'Mi': 1024**2,
            'Gi': 1024**3,
            'Ti': 1024**4,
            'Pi': 1024**5,
            'Ei': 1024**6,
        }
        
        # Decimal units (powers of 1000)
        decimal_units = {
            'k': 1000,
            'K': 1000,
            'M': 1000**2,
            'G': 1000**3,
            'T': 1000**4,
            'P': 1000**5,
            'E': 1000**6,
        }
        
        # Check for units
        for unit, multiplier in binary_units.items():
            if memory_str.endswith(unit):
                value = float(memory_str[:-len(unit)])
                return int(value * multiplier / (1024**2))  # Convert to MiB
        
        for unit, multiplier in decimal_units.items():
            if memory_str.endswith(unit):
                value = float(memory_str[:-len(unit)])
                return int(value * multiplier / (1024**2))  # Convert to MiB
        
        # Assume bytes if no unit
        return int(float(memory_str) / (1024**2))
```

### Fix 4: Resource Value Validation in `config_validator.py:227`
Update the _validate_resource_value method with stricter regex:
```python
def _validate_resource_value(self, value: str) -> bool:
    """Validate Kubernetes resource value format."""
    import re
    # CPU: number (int or float) with optional 'm' suffix, or with units u/n
    # Also support scientific notation like 1e3m or 1.5e-3
    cpu_pattern = r'^([0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?)(m|u|n)?$'
    
    # Memory: number with optional valid binary or decimal suffix
    # Ki, Mi, Gi, Ti, Pi, Ei (binary) or k, K, M, G, T, P, E (decimal)
    memory_pattern = r'^([0-9]+(\.[0-9]+)?)(Ki|Mi|Gi|Ti|Pi|Ei|k|K|M|G|T|P|E)?$'
    
    value_str = str(value).strip()
    
    # Check if it matches CPU pattern
    if re.fullmatch(cpu_pattern, value_str):
        return True
    
    # Check if it matches memory pattern
    if re.fullmatch(memory_pattern, value_str):
        return True
    
    # Check if it's a plain number (bytes or cores)
    if re.fullmatch(r'^[0-9]+(\.[0-9]+)?$', value_str):
        return True
    
    return False
```

## Security Fixes

### Security Fix 1: SSL Verification in `integration_tester.py:394`
For the ingress routing test, make SSL verification configurable:
```python
# Add a parameter to the method or use instance variable
verify_ssl = getattr(self, 'verify_external_ssl', True)

response = requests.head(
    endpoint.external_url,
    timeout=self.short_timeout,
    verify=verify_ssl,
    allow_redirects=True
)
```

### Security Fix 2: Document Sleep in `service_checker.py:170`
The sleep is already documented as "Wait before retry to avoid overwhelming the API server" - this is intentional and necessary.

### Security Fix 3: SSL Verification in `service_checker.py:232`
For health checks within the cluster, make it configurable:
```python
# Add instance variable for internal SSL verification
verify_internal = getattr(self, 'verify_internal_ssl', False)

response = requests.get(url, timeout=10, verify=verify_internal)
```

## Additional Code Quality Improvements
Also apply the following Sourcery suggestions where they make sense:
1. Merge nested if conditions using `and` where appropriate
2. Use `re.fullmatch` instead of `re.match` for exact matching
3. Keep the `sum(1 for ...)` pattern as is - it's more readable than `sum(bool(...))`
