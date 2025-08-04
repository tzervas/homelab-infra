#!/usr/bin/env python3
"""Enhanced Configuration Schema Validator for Homelab Infrastructure"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import jsonschema
import yaml

# Schema definitions for different configuration types
HELM_ENVIRONMENT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["global"],
    "properties": {
        "global": {
            "type": "object",
            "required": ["environment", "domain"],
            "properties": {
                "environment": {
                    "type": "string",
                    "enum": ["development", "staging", "production", "template"]
                },
                "domain": {
                    "type": "string",
                    "pattern": "^([a-zA-Z0-9.-]+|\\${[A-Z_]+})$"
                },
                "tls": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "issuer": {"type": "string"}
                    }
                }
            }
        },
        "resources": {
            "type": "object",
            "properties": {
                "limits": {"$ref": "#/definitions/resourceSpec"},
                "requests": {"$ref": "#/definitions/resourceSpec"}
            }
        }
    },
    "definitions": {
        "resourceSpec": {
            "type": "object",
            "properties": {
                "cpu": {"type": "string"},
                "memory": {"type": "string"}
            }
        }
    }
}

ENVIRONMENT_CONFIG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["environment"],
    "properties": {
        "environment": {
            "type": "string",
            "enum": ["development", "staging", "production", "template"]
        },
        "global": {"type": "object"},
        "secrets": {"type": "object"},
        "tls": {"type": "object"},
        "metadata": {"type": "object"}
    }
}

ANSIBLE_INVENTORY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "all": {
            "type": "object",
            "properties": {
                "hosts": {"type": "object"},
                "children": {"type": "object"},
                "vars": {"type": "object"}
            }
        }
    }
}

class ConfigValidator:
    def __init__(self, log_level: str = "INFO"):
        self.logger = self._setup_logging(log_level)
        self.errors: List[str] = []
        
    def _setup_logging(self, level: str) -> logging.Logger:
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, level.upper()))
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
        
    def validate_helm_environment_config(self, config_path: Path) -> bool:
        """Validate Helm environment configuration file"""
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                
            if not config:
                self.logger.warning(f"⚠️ {config_path}: Empty configuration file")
                return True  # Empty files are acceptable
                
            jsonschema.validate(config, HELM_ENVIRONMENT_SCHEMA)
            self.logger.info(f"✅ {config_path}: Valid Helm environment configuration")
            return True
            
        except jsonschema.ValidationError as e:
            error_msg = f"❌ {config_path}: Helm schema validation failed - {e.message}"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return False
            
        except Exception as e:
            error_msg = f"❌ {config_path}: Failed to validate - {e}"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return False
            
    def validate_environment_config(self, config_path: Path) -> bool:
        """Validate environment-specific configuration file"""
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                
            if not config:
                self.logger.warning(f"⚠️ {config_path}: Empty configuration file")
                return True
                
            jsonschema.validate(config, ENVIRONMENT_CONFIG_SCHEMA)
            self.logger.info(f"✅ {config_path}: Valid environment configuration")
            return True
            
        except jsonschema.ValidationError as e:
            error_msg = f"❌ {config_path}: Environment schema validation failed - {e.message}"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return False
            
        except Exception as e:
            error_msg = f"❌ {config_path}: Failed to validate - {e}"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return False
            
    def validate_ansible_inventory(self, config_path: Path) -> bool:
        """Validate Ansible inventory file"""
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                
            if not config:
                self.logger.warning(f"⚠️ {config_path}: Empty inventory file")
                return False
                
            # Basic validation for Ansible inventory structure
            if 'all' not in config:
                self.logger.warning(f"⚠️ {config_path}: No 'all' group in inventory")
                
            self.logger.info(f"✅ {config_path}: Valid Ansible inventory")
            return True
            
        except Exception as e:
            error_msg = f"❌ {config_path}: Failed to validate Ansible inventory - {e}"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return False
            
    def detect_file_type(self, config_path: Path) -> str:
        """Detect configuration file type based on path and content"""
        path_str = str(config_path).lower()
        
        # Skip Kubernetes manifest files
        if config_path.name.endswith('.k8s.yaml') or config_path.name.endswith('.k8s.yml'):
            return "kubernetes_manifest"
            
        # Detect by path patterns
        if "helm" in path_str and "environments" in path_str:
            if "values" in config_path.name:
                return "helm_environment"
            elif "secrets" in config_path.name:
                return "environment_config"
                
        if "inventory" in path_str or config_path.name == "hosts.yml":
            return "ansible_inventory"
            
        if "environments" in path_str or config_path.parent.name == "environments":
            return "environment_config"
            
        return "generic"
        
    def validate_file(self, config_path: Path) -> bool:
        """Validate a single configuration file"""
        if not config_path.exists():
            error_msg = f"❌ {config_path}: File does not exist"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return False
            
        file_type = self.detect_file_type(config_path)
        
        # Skip Kubernetes manifests
        if file_type == "kubernetes_manifest":
            self.logger.info(f"⏭️ {config_path}: Skipping Kubernetes manifest file")
            return True
            
        # Route to appropriate validator
        if file_type == "helm_environment":
            return self.validate_helm_environment_config(config_path)
        elif file_type == "environment_config":
            return self.validate_environment_config(config_path)
        elif file_type == "ansible_inventory":
            return self.validate_ansible_inventory(config_path)
        else:
            # Generic YAML validation
            try:
                with open(config_path) as f:
                    yaml.safe_load(f)
                self.logger.info(f"✅ {config_path}: Valid YAML file")
                return True
            except Exception as e:
                error_msg = f"❌ {config_path}: Invalid YAML - {e}"
                self.logger.error(error_msg)
                self.errors.append(error_msg)
                return False
                
    def validate_all_configs(self, config_paths: List[str], environment: str = None) -> bool:
        """Validate all configuration files"""
        all_valid = True
        total_files = 0
        valid_files = 0
        
        for config_path_str in config_paths:
            config_path = Path(config_path_str)
            
            if config_path.is_dir():
                # Validate all YAML files in directory
                for yaml_file in config_path.glob("**/*.yaml"):
                    total_files += 1
                    if self.validate_file(yaml_file):
                        valid_files += 1
                    else:
                        all_valid = False
                        
                for yml_file in config_path.glob("**/*.yml"):
                    total_files += 1
                    if self.validate_file(yml_file):
                        valid_files += 1
                    else:
                        all_valid = False
            else:
                total_files += 1
                if self.validate_file(config_path):
                    valid_files += 1
                else:
                    all_valid = False
                    
        # Summary
        self.logger.info(f"\n📊 Validation Summary:")
        self.logger.info(f"Total files: {total_files}")
        self.logger.info(f"Valid files: {valid_files}")
        self.logger.info(f"Invalid files: {total_files - valid_files}")
        
        if environment:
            self.logger.info(f"Target environment: {environment}")
            
        return all_valid

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced homelab configuration validator")
    parser.add_argument("--config-paths", nargs="+", required=True,
                       help="Paths to configuration files or directories")
    parser.add_argument("--environment", 
                       choices=["development", "staging", "production"])
    parser.add_argument("--log-level", default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--fail-fast", action="store_true",
                       help="Stop on first validation error")
    
    args = parser.parse_args()
    
    validator = ConfigValidator(args.log_level)
    
    if validator.validate_all_configs(args.config_paths, args.environment):
        print("\n🎉 All configuration files are valid!")
        sys.exit(0)
    else:
        print(f"\n❌ Validation failed with {len(validator.errors)} errors:")
        for error in validator.errors:
            print(f"  {error}")
        sys.exit(1)

if __name__ == "__main__":
    main()