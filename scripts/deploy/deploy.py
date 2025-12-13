#!/usr/bin/env python3
"""
Homelab Infrastructure Deployment Orchestrator
Docker Compose based deployment automation for PoC/MVP phase
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    OKCYAN = '\033[96m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class HomelabDeployer:
    """Main deployment orchestrator for homelab infrastructure"""
    
    def __init__(self, docker_dir: Path, verbose: bool = False):
        self.docker_dir = docker_dir
        self.verbose = verbose
        self.compose_file = docker_dir / "docker-compose.yml"
        self.env_file = docker_dir / ".env"
        
    def print_header(self, message: str):
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{message}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
    
    def print_success(self, message: str):
        print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")
    
    def print_error(self, message: str):
        print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")
    
    def print_warning(self, message: str):
        print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")
    
    def print_info(self, message: str):
        print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")
    
    def check_prerequisites(self) -> bool:
        self.print_header("Checking Prerequisites")
        for tool, cmd in [("docker", "docker --version"), ("docker-compose", "docker-compose --version")]:
            try:
                subprocess.run(cmd.split(), capture_output=True, check=True)
                self.print_success(f"{tool} is installed")
            except:
                self.print_error(f"{tool} is not installed")
                return False
        return True
    
    def deploy(self, services: Optional[List[str]] = None):
        self.print_header("Deploying Homelab Infrastructure")
        os.chdir(self.docker_dir)
        cmd = ["docker-compose", "up", "-d"]
        if services:
            cmd.extend(services)
        try:
            subprocess.run(cmd, check=True)
            self.print_success("Deployment completed")
            return True
        except:
            self.print_error("Deployment failed")
            return False
    
    def status(self):
        self.print_header("Service Status")
        os.chdir(self.docker_dir)
        subprocess.run(["docker-compose", "ps"])
    
    def stop(self, services: Optional[List[str]] = None):
        self.print_header("Stopping Services")
        os.chdir(self.docker_dir)
        cmd = ["docker-compose", "stop"]
        if services:
            cmd.extend(services)
        subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(description="Homelab Infrastructure Deployment Orchestrator")
    parser.add_argument("action", choices=["deploy", "status", "stop"], help="Action to perform")
    parser.add_argument("--services", nargs="+", help="Specific services to target")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--docker-dir", type=Path, default=Path(__file__).parent.parent.parent / "docker")
    args = parser.parse_args()
    
    deployer = HomelabDeployer(args.docker_dir, verbose=args.verbose)
    
    if args.action == "deploy":
        if not deployer.check_prerequisites():
            sys.exit(1)
        if not deployer.deploy(args.services):
            sys.exit(1)
        deployer.print_success("\n🎉 Deployment completed!")
        deployer.print_info("Access services at:")
        deployer.print_info("  Portal: http://localhost:8000")
        deployer.print_info("  Keycloak: http://localhost:8080")
        deployer.print_info("  Grafana: http://localhost:3000")
    elif args.action == "status":
        deployer.status()
    elif args.action == "stop":
        deployer.stop(args.services)


if __name__ == "__main__":
    main()
