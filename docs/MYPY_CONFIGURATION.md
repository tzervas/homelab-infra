# MyPy Configuration Guide

This document explains the enhanced MyPy configuration for the homelab infrastructure project.

## Overview

The project uses MyPy for static type checking with strict settings to catch potential type-related issues early in development.

## Configuration Files

MyPy configuration is defined in two places:

1. **`pyproject.toml`** - Primary configuration (under `[tool.mypy]` section)
2. **`mypy.ini`** - Alternative configuration file with the same settings

Both files contain identical configurations; you can use either based on your preference.

## Strict Type Checking Options

The following strict options are enabled:

### Core Strictness Settings

- `disallow_untyped_defs = true` - All functions must have type annotations
- `disallow_incomplete_defs = true` - Functions with incomplete type annotations are not allowed
- `strict_optional = true` - Strict handling of Optional types
- `warn_unreachable = true` - Warn about unreachable code

### Additional Quality Checks

- `warn_return_any = true` - Warn when returning Any type from typed functions
- `warn_unused_configs = true` - Warn about unused mypy config sections
- `check_untyped_defs = true` - Type check inside untyped functions
- `no_implicit_optional = true` - Don't assume Optional for default None arguments
- `warn_redundant_casts = true` - Warn about unnecessary type casts
- `warn_unused_ignores = true` - Warn about unnecessary `# type: ignore` comments
- `warn_no_return = true` - Warn about missing return statements

### Output Configuration

- `show_error_codes = true` - Display error codes for easier suppression
- `show_column_numbers = true` - Show column numbers in error messages
- `pretty = true` - Use pretty output formatting
- `show_absolute_path = true` - Show absolute file paths in errors

## Module Overrides

### Third-Party Libraries Without Type Stubs

The following libraries don't provide type stubs, so we ignore import errors:

- `kubernetes.*`
- `yaml.*`
- `ansible.*`, `ansible_core.*`
- `dotenv.*`
- `bandit.*`, `safety.*`
- `yamllint.*`, `ansible_lint.*`
- `pytest.*`, `_pytest.*`
- `pkg_resources.*`, `setuptools.*`

### Test Files

Test files have relaxed type checking to allow for more flexible test code:

```toml
[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
disallow_incomplete_defs = false
```

## Type Stubs

The project includes type stub packages for better type checking:

- `types-PyYAML>=6.0.12` - Type stubs for PyYAML
- `types-requests>=2.31.0` - Type stubs for requests
- `types-jsonschema>=4.19.0` - Type stubs for jsonschema

## Running MyPy

### Command Line

```bash
# Check a single file
.venv/bin/mypy scripts/testing/config.py

# Check entire scripts directory
.venv/bin/mypy scripts

# Use specific config file
.venv/bin/mypy --config-file mypy.ini scripts
```

### With UV (recommended)

```bash
# After installing with uv sync --all-extras
uv run python -m mypy scripts
```

### Pre-commit Hook

MyPy runs automatically as part of pre-commit hooks:

```bash
# Install pre-commit hooks
uv tool install pre-commit
pre-commit install

# Run manually
pre-commit run mypy --all-files
```

## Common Issues and Solutions

### 1. Missing Type Annotations

```python
# Bad
def process_data(data):
    return data.upper()

# Good
def process_data(data: str) -> str:
    return data.upper()
```

### 2. Optional Types

```python
# Bad
def get_config(path: str = None) -> dict:
    ...

# Good
from typing import Optional
def get_config(path: Optional[str] = None) -> dict:
    ...
```

### 3. Any Types

```python
# Bad
from typing import Any
def process(data: Any) -> Any:
    ...

# Good
from typing import Union, Dict, List
def process(data: Union[Dict[str, str], List[str]]) -> Dict[str, str]:
    ...
```

### 4. Unreachable Code

```python
# Bad
def check_value(x: int) -> bool:
    if isinstance(x, int):
        return True
    return False  # This is unreachable

# Good
def check_value(x: int) -> bool:
    return True  # x is always int due to type annotation
```

## Gradual Adoption

If you have existing code without type annotations:

1. Start by adding `# type: ignore` comments to suppress errors
2. Gradually add type annotations file by file
3. Remove `# type: ignore` comments as you add proper types
4. Use `reveal_type()` to understand inferred types during development

## Integration with IDEs

Most Python IDEs support MyPy:

- **VS Code**: Install the Pylance extension
- **PyCharm**: MyPy support is built-in
- **Vim/Neovim**: Use ALE or coc-pyright

## Best Practices

1. **Be Specific**: Use specific types instead of Any when possible
2. **Use Type Aliases**: Create type aliases for complex types
3. **Document Complex Types**: Add comments explaining complex type annotations
4. **Gradual Typing**: Start with critical modules and expand coverage
5. **CI Integration**: Run MyPy in CI/CD pipelines to catch issues early

## Further Reading

- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [PEP 484 - Type Hints](https://www.python.org/dev/peps/pep-0484/)
