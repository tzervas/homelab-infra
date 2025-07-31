"""Portal Manager for Homelab Orchestrator.

Provides web interface for homelab management with security dashboard.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Gauge, Histogram, generate_latest

from homelab_orchestrator.core.config_manager import ConfigManager
from homelab_orchestrator.core.health import HealthMonitor
from homelab_orchestrator.core.security import SecurityManager


# Prometheus metrics
portal_requests = Counter("homelab_portal_requests_total", "Total requests to portal")
portal_errors = Counter("homelab_portal_errors_total", "Total errors in portal")
service_health_gauge = Gauge(
    "homelab_service_health",
    "Service health status",
    ["service", "namespace"],
)
api_latency = Histogram("homelab_api_latency_seconds", "API latency")


class PortalManager:
    """Manages the web portal for homelab infrastructure."""

    def __init__(
        self,
        config_manager: ConfigManager,
        health_monitor: HealthMonitor | None = None,
        security_manager: SecurityManager | None = None,
        project_root: Path | None = None,
    ) -> None:
        """Initialize the portal manager.

        Args:
            config_manager: Configuration manager instance
            health_monitor: Health monitoring instance
            security_manager: Security manager instance
            project_root: Project root directory
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.health_monitor = health_monitor
        self.security_manager = security_manager
        self.project_root = project_root or Path.cwd()

        # Initialize FastAPI app
        self.app = self._create_app()

        # Portal configuration
        self.host = "0.0.0.0"
        self.port = 8000
        self.running = False

        self.logger.info("Portal Manager initialized")

    def _create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        app = FastAPI(
            title="Homelab Portal",
            description="Central management portal for homelab infrastructure",
            version="0.4.0",
        )

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://homelab.local"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Mount static files
        static_path = self.project_root / "homelab_orchestrator" / "portal" / "static"
        if static_path.exists():
            app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

        # Register routes
        self._register_routes(app)

        return app

    def _register_routes(self, app: FastAPI) -> None:
        """Register API routes."""

        @app.get("/", response_class=HTMLResponse)
        async def index(request: Request) -> HTMLResponse:
            """Serve the main portal page."""
            portal_requests.inc()
            return await self.render_portal_page()

        @app.get("/api/health")
        async def health() -> dict[str, Any]:
            """Health check endpoint."""
            return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

        @app.get("/api/services")
        async def get_services() -> list[dict[str, Any]]:
            """Get all monitored services with their status."""
            portal_requests.inc()

            if not self.health_monitor:
                return []

            services = []
            service_configs = self.config_manager.get_services_config()

            for service_name, service_config in service_configs.get("discovery", {}).items():
                if isinstance(service_config, dict) and "namespace" in service_config:
                    health_status = await self.health_monitor.check_service_health(
                        service_name,
                        service_config["namespace"],
                    )

                    service_info = {
                        "name": service_name.replace("_", " ").title(),
                        "namespace": service_config["namespace"],
                        "status": health_status.get("status", "unknown"),
                        "url": service_configs.get("urls", {})
                        .get("external", {})
                        .get(service_name, ""),
                        "health": health_status,
                    }

                    # Update Prometheus gauge
                    health_value = 1 if health_status.get("status") == "healthy" else 0
                    service_health_gauge.labels(
                        service=service_name,
                        namespace=service_config["namespace"],
                    ).set(health_value)

                    services.append(service_info)

            return services

        @app.get("/api/security/metrics")
        async def get_security_metrics() -> dict[str, Any]:
            """Get security metrics for the dashboard."""
            portal_requests.inc()

            if not self.security_manager:
                raise HTTPException(status_code=503, detail="Security manager not available")

            try:
                return await self.security_manager.get_security_metrics()
            except Exception as e:
                portal_errors.inc()
                self.logger.exception(f"Error getting security metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/security/certificates")
        async def get_certificates() -> list[dict[str, Any]]:
            """Get certificate information."""
            portal_requests.inc()

            if not self.security_manager:
                return []

            try:
                return await self.security_manager.get_certificate_status()
            except Exception as e:
                portal_errors.inc()
                self.logger.exception(f"Error getting certificates: {e}")
                return []

        @app.get("/api/security/alerts")
        async def get_security_alerts() -> list[dict[str, Any]]:
            """Get recent security alerts."""
            portal_requests.inc()

            if not self.security_manager:
                return []

            try:
                return await self.security_manager.get_recent_alerts()
            except Exception as e:
                portal_errors.inc()
                self.logger.exception(f"Error getting security alerts: {e}")
                return []

        @app.get("/metrics")
        async def metrics() -> str:
            """Prometheus metrics endpoint."""
            return generate_latest().decode("utf-8")

    async def render_portal_page(self) -> HTMLResponse:
        """Render the main portal HTML page."""
        # For now, we'll return the enhanced HTML directly
        # In production, this would use Jinja2 templates
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Homelab Portal</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            padding: 30px;
            margin-bottom: 30px;
            text-align: center;
        }

        .header h1 {
            color: #333;
            font-size: 2.5rem;
            margin-bottom: 10px;
        }

        .header p {
            color: #666;
            font-size: 1.1rem;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .dashboard-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
        }

        .dashboard-card h2 {
            color: #333;
            font-size: 1.5rem;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }

        .service-card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            text-decoration: none;
            color: inherit;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }

        .service-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            border-color: #667eea;
        }

        .service-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .service-icon {
            font-size: 2rem;
        }

        .service-status {
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .status-healthy { background: #d4edda; color: #155724; }
        .status-degraded { background: #fff3cd; color: #856404; }
        .status-unhealthy { background: #f8d7da; color: #721c24; }
        .status-unknown { background: #e2e3e5; color: #383d41; }

        .security-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }

        .metric-item {
            background: #f1f3f4;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }

        .metric-value {
            font-size: 2rem;
            font-weight: bold;
            color: #333;
        }

        .metric-label {
            font-size: 0.9rem;
            color: #666;
            margin-top: 5px;
        }

        .alert-list {
            max-height: 300px;
            overflow-y: auto;
        }

        .alert-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid #dc3545;
        }

        .alert-critical { border-color: #dc3545; }
        .alert-high { border-color: #fd7e14; }
        .alert-medium { border-color: #ffc107; }
        .alert-low { border-color: #20c997; }
        .alert-info { border-color: #17a2b8; }

        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }

        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏠 Homelab Portal</h1>
            <p>Central management and security dashboard for your infrastructure</p>
        </div>

        <div class="dashboard-grid">
            <!-- Services Status -->
            <div class="dashboard-card">
                <h2>📊 Services Status</h2>
                <div id="services-container" class="services-grid">
                    <div class="loading">Loading services...</div>
                </div>
            </div>

            <!-- Security Overview -->
            <div class="dashboard-card">
                <h2>🔐 Security Overview</h2>
                <div id="security-metrics" class="security-metrics">
                    <div class="loading">Loading security metrics...</div>
                </div>
            </div>

            <!-- Recent Alerts -->
            <div class="dashboard-card">
                <h2>🚨 Recent Alerts</h2>
                <div id="alerts-container" class="alert-list">
                    <div class="loading">Loading alerts...</div>
                </div>
            </div>

            <!-- Certificate Status -->
            <div class="dashboard-card">
                <h2>🔒 Certificate Status</h2>
                <div id="certificates-container">
                    <div class="loading">Loading certificates...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Auto-refresh interval (30 seconds)
        const REFRESH_INTERVAL = 30000;

        async function fetchServices() {
            try {
                const response = await fetch('/api/services');
                const services = await response.json();

                const container = document.getElementById('services-container');
                if (services.length === 0) {
                    container.innerHTML = '<p>No services configured</p>';
                    return;
                }

                container.innerHTML = services.map(service => `
                    <a href="${service.url || '#'}" class="service-card" ${service.url ? 'target="_blank"' : ''}>
                        <div class="service-header">
                            <span class="service-icon">${getServiceIcon(service.name)}</span>
                            <span class="service-status status-${service.status}">${service.status}</span>
                        </div>
                        <div><strong>${service.name}</strong></div>
                        <div style="font-size: 0.85rem; color: #666;">${service.namespace}</div>
                    </a>
                `).join('');
            } catch (error) {
                document.getElementById('services-container').innerHTML =
                    '<div class="error">Failed to load services</div>';
            }
        }

        async function fetchSecurityMetrics() {
            try {
                const response = await fetch('/api/security/metrics');
                const metrics = await response.json();

                const container = document.getElementById('security-metrics');
                container.innerHTML = `
                    <div class="metric-item">
                        <div class="metric-value">${metrics.security_score || 0}</div>
                        <div class="metric-label">Security Score</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-value">${metrics.total_services || 0}</div>
                        <div class="metric-label">Total Services</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-value">${metrics.healthy_services || 0}</div>
                        <div class="metric-label">Healthy Services</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-value">${metrics.active_alerts || 0}</div>
                        <div class="metric-label">Active Alerts</div>
                    </div>
                `;
            } catch (error) {
                document.getElementById('security-metrics').innerHTML =
                    '<div class="error">Failed to load security metrics</div>';
            }
        }

        async function fetchAlerts() {
            try {
                const response = await fetch('/api/security/alerts');
                const alerts = await response.json();

                const container = document.getElementById('alerts-container');
                if (alerts.length === 0) {
                    container.innerHTML = '<p>No recent alerts</p>';
                    return;
                }

                container.innerHTML = alerts.slice(0, 10).map(alert => `
                    <div class="alert-item alert-${alert.severity}">
                        <div><strong>${alert.title}</strong></div>
                        <div style="font-size: 0.85rem; margin-top: 5px;">${alert.description}</div>
                        <div style="font-size: 0.75rem; color: #666; margin-top: 5px;">
                            ${new Date(alert.timestamp).toLocaleString()}
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                document.getElementById('alerts-container').innerHTML =
                    '<div class="error">Failed to load alerts</div>';
            }
        }

        async function fetchCertificates() {
            try {
                const response = await fetch('/api/security/certificates');
                const certificates = await response.json();

                const container = document.getElementById('certificates-container');
                if (certificates.length === 0) {
                    container.innerHTML = '<p>No certificates found</p>';
                    return;
                }

                container.innerHTML = `
                    <div class="security-metrics">
                        ${certificates.map(cert => `
                            <div class="metric-item">
                                <div style="font-weight: bold;">${cert.common_name}</div>
                                <div style="font-size: 0.85rem; color: ${cert.days_until_expiry < 30 ? '#dc3545' : '#28a745'};">
                                    ${cert.days_until_expiry} days
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
            } catch (error) {
                document.getElementById('certificates-container').innerHTML =
                    '<div class="error">Failed to load certificates</div>';
            }
        }

        function getServiceIcon(serviceName) {
            const icons = {
                'Grafana': '📊',
                'Prometheus': '🔍',
                'Gitlab': '🚀',
                'Keycloak': '🔐',
                'Jupyterlab': '📓',
                'Jupyter': '📓',
                'Ollama': '🤖',
                'Longhorn': '💾',
            };
            return icons[serviceName] || '🔧';
        }

        // Initial load
        fetchServices();
        fetchSecurityMetrics();
        fetchAlerts();
        fetchCertificates();

        // Auto-refresh
        setInterval(() => {
            fetchServices();
            fetchSecurityMetrics();
            fetchAlerts();
            fetchCertificates();
        }, REFRESH_INTERVAL);
    </script>
</body>
</html>
        """
        return HTMLResponse(content=html_content)

    async def start(self) -> None:
        """Start the portal server."""
        if self.running:
            self.logger.warning("Portal is already running")
            return

        self.running = True
        self.logger.info(f"Starting portal on {self.host}:{self.port}")

        # The actual server start will be handled by uvicorn in the main script

    async def stop(self) -> None:
        """Stop the portal server."""
        if not self.running:
            return

        self.running = False
        self.logger.info("Portal stopped")
