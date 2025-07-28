#!/usr/bin/env python3
"""
Certificate Expiry Monitoring Script
Monitors certificate expiration dates and sends alerts for certificates nearing expiry.
"""

import os
import sys
import json
import logging
import subprocess
import smtplib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
import yaml
import requests

# Configure logging with user rule compliance
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/certificate-monitoring.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Certificate:
    """Certificate information data class."""
    name: str
    namespace: str
    issuer: str
    subject: str
    not_before: datetime
    not_after: datetime
    dns_names: List[str]
    days_until_expiry: int
    is_ca: bool = False
    secret_name: str = ""

@dataclass
class AlertConfig:
    """Alert configuration data class."""
    email_enabled: bool = True
    webhook_enabled: bool = False
    slack_enabled: bool = False
    warning_days: int = 30
    critical_days: int = 7
    email_recipient: str = "tz-dev@vectorweight.com"
    webhook_url: str = ""
    slack_webhook_url: str = ""

class CertificateMonitor:
    """Certificate expiry monitoring class."""
    
    def __init__(self, config_file: str = "/etc/security/cert-monitoring-config.yaml"):
        """Initialize the certificate monitor."""
        self.config = self._load_config(config_file)
        self.alert_config = AlertConfig(**self.config.get('alerts', {}))
        self.certificates: List[Certificate] = []
        
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_file} not found, using defaults")
            return {
                'alerts': {
                    'email_enabled': True,
                    'webhook_enabled': False,
                    'slack_enabled': False,
                    'warning_days': 30,
                    'critical_days': 7,
                    'email_recipient': 'tz-dev@vectorweight.com'
                },
                'monitoring': {
                    'check_k8s_certificates': True,
                    'check_file_certificates': True,
                    'check_remote_certificates': True
                }
            }
    
    def run_kubectl_command(self, args: List[str]) -> Tuple[str, int]:
        """Run kubectl command and return output and exit code."""
        try:
            cmd = ['kubectl'] + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout, result.returncode
        except subprocess.TimeoutExpired:
            logger.error(f"kubectl command timed out: {' '.join(args)}")
            return "", 1
        except Exception as e:
            logger.error(f"Error running kubectl command: {e}")
            return "", 1
    
    def get_kubernetes_certificates(self) -> List[Certificate]:
        """Get certificates from Kubernetes cert-manager."""
        certificates = []
        
        # Get cert-manager certificates
        output, exit_code = self.run_kubectl_command([
            'get', 'certificates', '-A', '-o', 'json'
        ])
        
        if exit_code != 0:
            logger.error("Failed to get certificates from Kubernetes")
            return certificates
        
        try:
            cert_data = json.loads(output)
            for item in cert_data.get('items', []):
                cert = self._parse_k8s_certificate(item)
                if cert:
                    certificates.append(cert)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse certificate JSON: {e}")
        
        return certificates
    
    def _parse_k8s_certificate(self, cert_data: Dict) -> Optional[Certificate]:
        """Parse Kubernetes certificate data."""
        try:
            metadata = cert_data.get('metadata', {})
            spec = cert_data.get('spec', {})
            status = cert_data.get('status', {})
            
            name = metadata.get('name', 'unknown')
            namespace = metadata.get('namespace', 'default')
            secret_name = spec.get('secretName', '')
            
            # Get certificate details from status
            conditions = status.get('conditions', [])
            not_after_str = None
            
            for condition in conditions:
                if condition.get('type') == 'Ready' and condition.get('status') == 'True':
                    # Get the actual certificate from the secret
                    secret_output, secret_exit_code = self.run_kubectl_command([
                        'get', 'secret', secret_name, '-n', namespace, '-o', 'json'
                    ])
                    
                    if secret_exit_code == 0:
                        try:
                            secret_data = json.loads(secret_output)
                            tls_crt = secret_data.get('data', {}).get('tls.crt', '')
                            if tls_crt:
                                cert_info = self._parse_certificate_data(tls_crt)
                                if cert_info:
                                    return Certificate(
                                        name=name,
                                        namespace=namespace,
                                        issuer=spec.get('issuerRef', {}).get('name', 'unknown'),
                                        subject=cert_info['subject'],
                                        not_before=cert_info['not_before'],
                                        not_after=cert_info['not_after'],
                                        dns_names=spec.get('dnsNames', []),
                                        days_until_expiry=self._calculate_days_until_expiry(cert_info['not_after']),
                                        is_ca=spec.get('isCA', False),
                                        secret_name=secret_name
                                    )
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.error(f"Failed to parse secret data for {name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error parsing certificate data: {e}")
        
        return None
    
    def _parse_certificate_data(self, cert_data_b64: str) -> Optional[Dict]:
        """Parse base64 encoded certificate data."""
        try:
            import base64
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            
            # Decode base64 certificate
            cert_data = base64.b64decode(cert_data_b64)
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            return {
                'subject': cert.subject.rfc4514_string(),
                'issuer': cert.issuer.rfc4514_string(),
                'not_before': cert.not_valid_before,
                'not_after': cert.not_valid_after,
                'serial_number': str(cert.serial_number)
            }
        except Exception as e:
            logger.error(f"Failed to parse certificate data: {e}")
            return None
    
    def _calculate_days_until_expiry(self, not_after: datetime) -> int:
        """Calculate days until certificate expiry."""
        if not_after.tzinfo is None:
            not_after = not_after.replace(tzinfo=datetime.now().astimezone().tzinfo)
        
        now = datetime.now().astimezone()
        delta = not_after - now
        return delta.days
    
    def check_file_certificates(self, cert_paths: List[str]) -> List[Certificate]:
        """Check certificates from file paths."""
        certificates = []
        
        for cert_path in cert_paths:
            try:
                cert_info = self._get_file_certificate_info(cert_path)
                if cert_info:
                    certificates.append(cert_info)
            except Exception as e:
                logger.error(f"Failed to check certificate {cert_path}: {e}")
        
        return certificates
    
    def _get_file_certificate_info(self, cert_path: str) -> Optional[Certificate]:
        """Get certificate information from file."""
        try:
            # Use openssl to get certificate info
            cmd = ['openssl', 'x509', '-in', cert_path, '-text', '-noout']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"Failed to read certificate {cert_path}: {result.stderr}")
                return None
            
            # Parse openssl output
            output = result.stdout
            subject = self._extract_openssl_field(output, 'Subject:')
            issuer = self._extract_openssl_field(output, 'Issuer:')
            not_before_str = self._extract_openssl_field(output, 'Not Before:')
            not_after_str = self._extract_openssl_field(output, 'Not After :')
            
            if not all([subject, issuer, not_before_str, not_after_str]):
                logger.error(f"Failed to parse certificate fields for {cert_path}")
                return None
            
            not_before = datetime.strptime(not_before_str.strip(), '%b %d %H:%M:%S %Y %Z')
            not_after = datetime.strptime(not_after_str.strip(), '%b %d %H:%M:%S %Y %Z')
            
            return Certificate(
                name=os.path.basename(cert_path),
                namespace="file-system",
                issuer=issuer,
                subject=subject,
                not_before=not_before,
                not_after=not_after,
                dns_names=[],
                days_until_expiry=self._calculate_days_until_expiry(not_after),
                is_ca=False,
                secret_name=""
            )
            
        except Exception as e:
            logger.error(f"Error getting file certificate info: {e}")
            return None
    
    def _extract_openssl_field(self, output: str, field_name: str) -> str:
        """Extract field value from openssl output."""
        lines = output.split('\n')
        for line in lines:
            if field_name in line:
                return line.split(field_name, 1)[1].strip()
        return ""
    
    def check_remote_certificates(self, hosts: List[Dict[str, str]]) -> List[Certificate]:
        """Check certificates from remote hosts."""
        certificates = []
        
        for host_config in hosts:
            hostname = host_config.get('hostname')
            port = host_config.get('port', 443)
            
            try:
                cert_info = self._get_remote_certificate_info(hostname, port)
                if cert_info:
                    certificates.append(cert_info)
            except Exception as e:
                logger.error(f"Failed to check remote certificate {hostname}:{port}: {e}")
        
        return certificates
    
    def _get_remote_certificate_info(self, hostname: str, port: int) -> Optional[Certificate]:
        """Get certificate information from remote host."""
        try:
            import ssl
            import socket
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            
            # Get certificate from remote host
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert_der = ssock.getpeercert(binary_form=True)
                    cert = x509.load_der_x509_certificate(cert_der, default_backend())
                    
                    return Certificate(
                        name=f"{hostname}:{port}",
                        namespace="remote",
                        issuer=cert.issuer.rfc4514_string(),
                        subject=cert.subject.rfc4514_string(),
                        not_before=cert.not_valid_before,
                        not_after=cert.not_valid_after,
                        dns_names=[],
                        days_until_expiry=self._calculate_days_until_expiry(cert.not_valid_after),
                        is_ca=False,
                        secret_name=""
                    )
                    
        except Exception as e:
            logger.error(f"Error getting remote certificate info: {e}")
            return None
    
    def send_email_alert(self, certificates: List[Certificate]) -> bool:
        """Send email alert for expiring certificates."""
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.config.get('email', {}).get('from', 'homelab@local')
            msg['To'] = self.alert_config.email_recipient
            msg['Subject'] = "Certificate Expiry Alert - Homelab Infrastructure"
            
            # Create email body
            body = self._create_email_body(certificates)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            smtp_config = self.config.get('email', {})
            server = smtplib.SMTP(
                smtp_config.get('host', 'localhost'),
                smtp_config.get('port', 587)
            )
            
            if smtp_config.get('tls', True):
                server.starttls()
            
            if smtp_config.get('username') and smtp_config.get('password'):
                server.login(smtp_config['username'], smtp_config['password'])
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email alert sent to {self.alert_config.email_recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def _create_email_body(self, certificates: List[Certificate]) -> str:
        """Create HTML email body for certificate alerts."""
        critical_certs = [c for c in certificates if c.days_until_expiry <= self.alert_config.critical_days]
        warning_certs = [c for c in certificates if self.alert_config.critical_days < c.days_until_expiry <= self.alert_config.warning_days]
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .critical {{ color: #d32f2f; background-color: #ffebee; padding: 10px; margin: 10px 0; }}
                .warning {{ color: #f57c00; background-color: #fff3e0; padding: 10px; margin: 10px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .expired {{ background-color: #ffebee; }}
                .critical-row {{ background-color: #ffcdd2; }}
                .warning-row {{ background-color: #ffe0b2; }}
            </style>
        </head>
        <body>
            <h2>Certificate Expiry Alert - Homelab Infrastructure</h2>
            <p>Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """
        
        if critical_certs:
            html_body += f"""
            <div class="critical">
                <h3>🚨 Critical: {len(critical_certs)} certificates expire within {self.alert_config.critical_days} days</h3>
            </div>
            """
        
        if warning_certs:
            html_body += f"""
            <div class="warning">
                <h3>⚠️ Warning: {len(warning_certs)} certificates expire within {self.alert_config.warning_days} days</h3>
            </div>
            """
        
        # Create certificate table
        html_body += """
            <table>
                <tr>
                    <th>Certificate Name</th>
                    <th>Namespace</th>
                    <th>Subject</th>
                    <th>Issuer</th>
                    <th>Expires</th>
                    <th>Days Left</th>
                    <th>Status</th>
                </tr>
        """
        
        all_certs = critical_certs + warning_certs
        for cert in sorted(all_certs, key=lambda x: x.days_until_expiry):
            row_class = ""
            status = ""
            
            if cert.days_until_expiry < 0:
                row_class = "expired"
                status = "EXPIRED"
            elif cert.days_until_expiry <= self.alert_config.critical_days:
                row_class = "critical-row"
                status = "CRITICAL"
            else:
                row_class = "warning-row"
                status = "WARNING"
            
            html_body += f"""
                <tr class="{row_class}">
                    <td>{cert.name}</td>
                    <td>{cert.namespace}</td>
                    <td>{cert.subject[:50]}...</td>
                    <td>{cert.issuer[:50]}...</td>
                    <td>{cert.not_after.strftime('%Y-%m-%d %H:%M:%S')}</td>
                    <td>{cert.days_until_expiry}</td>
                    <td>{status}</td>
                </tr>
            """
        
        html_body += """
            </table>
            <br>
            <p><small>This is an automated alert from the Homelab Certificate Monitoring System.</small></p>
        </body>
        </html>
        """
        
        return html_body
    
    def send_webhook_alert(self, certificates: List[Certificate]) -> bool:
        """Send webhook alert for expiring certificates."""
        if not self.alert_config.webhook_url:
            return False
        
        try:
            critical_certs = [c for c in certificates if c.days_until_expiry <= self.alert_config.critical_days]
            warning_certs = [c for c in certificates if self.alert_config.critical_days < c.days_until_expiry <= self.alert_config.warning_days]
            
            payload = {
                'timestamp': datetime.now().isoformat(),
                'source': 'homelab-certificate-monitor',
                'summary': {
                    'critical_count': len(critical_certs),
                    'warning_count': len(warning_certs),
                    'total_count': len(certificates)
                },
                'certificates': [
                    {
                        'name': cert.name,
                        'namespace': cert.namespace,
                        'days_until_expiry': cert.days_until_expiry,
                        'expires_at': cert.not_after.isoformat(),
                        'severity': 'critical' if cert.days_until_expiry <= self.alert_config.critical_days else 'warning'
                    }
                    for cert in certificates
                ]
            }
            
            response = requests.post(
                self.alert_config.webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info("Webhook alert sent successfully")
                return True
            else:
                logger.error(f"Webhook alert failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False
    
    def run_monitoring(self) -> None:
        """Run certificate monitoring check."""
        logger.info("Starting certificate expiry monitoring")
        
        # Collect certificates from various sources
        if self.config.get('monitoring', {}).get('check_k8s_certificates', True):
            k8s_certs = self.get_kubernetes_certificates()
            self.certificates.extend(k8s_certs)
            logger.info(f"Found {len(k8s_certs)} Kubernetes certificates")
        
        if self.config.get('monitoring', {}).get('check_file_certificates', True):
            file_paths = self.config.get('file_certificates', [])
            file_certs = self.check_file_certificates(file_paths)
            self.certificates.extend(file_certs)
            logger.info(f"Found {len(file_certs)} file certificates")
        
        if self.config.get('monitoring', {}).get('check_remote_certificates', True):
            remote_hosts = self.config.get('remote_certificates', [])
            remote_certs = self.check_remote_certificates(remote_hosts)
            self.certificates.extend(remote_certs)  
            logger.info(f"Found {len(remote_certs)} remote certificates")
        
        # Filter certificates that need alerts
        alert_certs = [
            cert for cert in self.certificates
            if cert.days_until_expiry <= self.alert_config.warning_days
        ]
        
        if alert_certs:
            logger.warning(f"Found {len(alert_certs)} certificates requiring alerts")
            
            # Send alerts
            if self.alert_config.email_enabled:
                self.send_email_alert(alert_certs)
            
            if self.alert_config.webhook_enabled:
                self.send_webhook_alert(alert_certs)
                
            # Log certificate details
            for cert in alert_certs:
                severity = "CRITICAL" if cert.days_until_expiry <= self.alert_config.critical_days else "WARNING"
                logger.warning(f"{severity}: {cert.name} in {cert.namespace} expires in {cert.days_until_expiry} days")
        else:
            logger.info("No certificates require alerts")
        
        logger.info("Certificate expiry monitoring completed")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Certificate Expiry Monitoring')
    parser.add_argument('--config', default='/etc/security/cert-monitoring-config.yaml',
                        help='Configuration file path')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        monitor = CertificateMonitor(args.config)
        monitor.run_monitoring()
    except Exception as e:
        logger.error(f"Certificate monitoring failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
