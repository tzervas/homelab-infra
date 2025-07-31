"""Webhook Manager - Unified webhook and event processing system.

Handles webhook endpoints, event processing, notifications, and integrations
with external systems for comprehensive homelab automation.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

import aiohttp
from aiohttp import web


if TYPE_CHECKING:
    from collections.abc import Callable

    from homelab_orchestrator.core.config_manager import ConfigManager


class WebhookManager:
    """Comprehensive webhook and event management system."""

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize webhook manager.

        Args:
            config_manager: Configuration manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager

        # Webhook configuration
        self.webhook_config = self._get_webhook_config()

        # Web application and server
        self.app: web.Application | None = None
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

        # Event handlers
        self.event_handlers: dict[str, list[Callable]] = {}

        # Notification endpoints
        self.notification_endpoints: list[dict[str, Any]] = []

        self._setup_webhook_app()

    def _get_webhook_config(self) -> dict[str, Any]:
        """Get webhook configuration from config manager."""
        return {
            "enabled": True,
            "host": "0.0.0.0",
            "port": 8080,
            "secret_token": "homelab-webhook-secret",  # Should be from secure config
            "endpoints": {
                "github": "/webhooks/github",
                "gitlab": "/webhooks/gitlab",
                "deployment": "/webhooks/deployment",
                "health": "/webhooks/health",
                "security": "/webhooks/security",
            },
        }

    def _setup_webhook_app(self) -> None:
        """Setup aiohttp web application for webhooks."""
        self.app = web.Application()

        # Add webhook routes
        webhook_endpoints = self.webhook_config.get("endpoints", {})

        self.app.router.add_post(
            webhook_endpoints.get("github", "/webhooks/github"),
            self._handle_github_webhook,
        )
        self.app.router.add_post(
            webhook_endpoints.get("gitlab", "/webhooks/gitlab"),
            self._handle_gitlab_webhook,
        )
        self.app.router.add_post(
            webhook_endpoints.get("deployment", "/webhooks/deployment"),
            self._handle_deployment_webhook,
        )
        self.app.router.add_post(
            webhook_endpoints.get("health", "/webhooks/health"),
            self._handle_health_webhook,
        )
        self.app.router.add_post(
            webhook_endpoints.get("security", "/webhooks/security"),
            self._handle_security_webhook,
        )

        # Health check endpoint
        self.app.router.add_get("/health", self._handle_health_check)

        # Status endpoint
        self.app.router.add_get("/status", self._handle_status_check)

        self.logger.debug("Webhook application configured")

    async def start(self) -> None:
        """Start webhook server."""
        if not self.webhook_config.get("enabled", True):
            self.logger.info("Webhook manager disabled")
            return

        if self.runner:
            self.logger.warning("Webhook server already running")
            return

        host = self.webhook_config.get("host", "0.0.0.0")
        port = self.webhook_config.get("port", 8080)

        self.logger.info(f"Starting webhook server on {host}:{port}")

        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, host, port)
            await self.site.start()

            self.logger.info(f"Webhook server started on {host}:{port}")

        except Exception as e:
            self.logger.exception(f"Failed to start webhook server: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop webhook server."""
        if self.site:
            await self.site.stop()
            self.site = None

        if self.runner:
            await self.runner.cleanup()
            self.runner = None

        self.logger.info("Webhook server stopped")

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Register event handler for specific event types.

        Args:
            event_type: Type of event to handle
            handler: Async function to handle the event
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []

        self.event_handlers[event_type].append(handler)
        self.logger.debug(f"Registered event handler for: {event_type}")

    async def emit_event(self, event_type: str, event_data: dict[str, Any]) -> None:
        """Emit event to registered handlers.

        Args:
            event_type: Type of event
            event_data: Event data payload
        """
        handlers = self.event_handlers.get(event_type, [])

        if not handlers:
            self.logger.debug(f"No handlers registered for event: {event_type}")
            return

        self.logger.info(f"Emitting event: {event_type} to {len(handlers)} handlers")

        # Execute handlers concurrently
        tasks = []
        for handler in handlers:
            task = asyncio.create_task(handler(event_data))
            tasks.append(task)

        # Wait for all handlers
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log handler failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Event handler {i} failed for {event_type}: {result}")

    async def send_notification(
        self,
        message: str,
        level: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Send notification to configured endpoints.

        Args:
            message: Notification message
            level: Notification level (info, warning, error, critical)
            metadata: Additional metadata
        """
        notification_data = {
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat(),
            "source": "homelab-orchestrator",
            "metadata": metadata or {},
        }

        self.logger.info(f"Sending {level} notification: {message}")

        # Send to all configured notification endpoints
        for endpoint in self.notification_endpoints:
            try:
                await self._send_to_endpoint(endpoint, notification_data)
            except Exception as e:
                self.logger.exception(f"Failed to send notification to {endpoint}: {e}")

    async def _send_to_endpoint(
        self,
        endpoint: dict[str, Any],
        data: dict[str, Any],
    ) -> None:
        """Send data to notification endpoint.

        Args:
            endpoint: Endpoint configuration
            data: Data to send
        """
        endpoint_type = endpoint.get("type", "webhook")
        endpoint_url = endpoint.get("url")

        if not endpoint_url:
            self.logger.warning(f"No URL configured for endpoint: {endpoint}")
            return

        if endpoint_type == "webhook":
            async with aiohttp.ClientSession() as session:
                headers = endpoint.get("headers", {})
                headers.setdefault("Content-Type", "application/json")

                async with session.post(
                    endpoint_url,
                    json=data,
                    headers=headers,
                    timeout=30,
                ) as response:
                    if response.status >= 400:
                        self.logger.warning(
                            f"Notification endpoint returned {response.status}: {endpoint_url}",
                        )

        elif endpoint_type == "slack":
            # Transform data for Slack
            slack_data = {
                "text": data["message"],
                "username": "Homelab Orchestrator",
                "icon_emoji": self._get_slack_emoji(data["level"]),
            }

            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    endpoint_url,
                    json=slack_data,
                    timeout=30,
                ) as response,
            ):
                if response.status >= 400:
                    self.logger.warning(
                        f"Slack notification failed with {response.status}",
                    )

    def _get_slack_emoji(self, level: str) -> str:
        """Get appropriate Slack emoji for notification level."""
        emoji_map = {
            "info": ":information_source:",
            "warning": ":warning:",
            "error": ":x:",
            "critical": ":rotating_light:",
        }
        return emoji_map.get(level, ":robot_face:")

    # Webhook handlers
    async def _handle_github_webhook(self, request: web.Request) -> web.Response:
        """Handle GitHub webhook events."""
        try:
            payload = await request.json()
            event_type = request.headers.get("X-GitHub-Event", "unknown")

            self.logger.info(f"Received GitHub webhook: {event_type}")

            # Process GitHub events
            if event_type == "push":
                await self._handle_github_push(payload)
            elif event_type == "pull_request":
                await self._handle_github_pull_request(payload)
            elif event_type == "release":
                await self._handle_github_release(payload)

            return web.json_response({"status": "processed"})

        except Exception as e:
            self.logger.exception(f"GitHub webhook processing failed: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_gitlab_webhook(self, request: web.Request) -> web.Response:
        """Handle GitLab webhook events."""
        try:
            payload = await request.json()
            event_type = request.headers.get("X-Gitlab-Event", "unknown")

            self.logger.info(f"Received GitLab webhook: {event_type}")

            # Process GitLab events
            if event_type == "Push Hook":
                await self._handle_gitlab_push(payload)
            elif event_type == "Merge Request Hook":
                await self._handle_gitlab_merge_request(payload)
            elif event_type == "Pipeline Hook":
                await self._handle_gitlab_pipeline(payload)

            return web.json_response({"status": "processed"})

        except Exception as e:
            self.logger.exception(f"GitLab webhook processing failed: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_deployment_webhook(self, request: web.Request) -> web.Response:
        """Handle deployment webhook events."""
        try:
            payload = await request.json()
            event_type = payload.get("event_type", "deployment")

            self.logger.info(f"Received deployment webhook: {event_type}")

            await self.emit_event(f"webhook.deployment.{event_type}", payload)

            return web.json_response({"status": "processed"})

        except Exception as e:
            self.logger.exception(f"Deployment webhook processing failed: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_health_webhook(self, request: web.Request) -> web.Response:
        """Handle health webhook events."""
        try:
            payload = await request.json()
            event_type = payload.get("event_type", "health")

            self.logger.info(f"Received health webhook: {event_type}")

            await self.emit_event(f"webhook.health.{event_type}", payload)

            # Send notification for critical health events
            if payload.get("level") in ["critical", "error"]:
                await self.send_notification(
                    f"Health alert: {payload.get('message', 'Unknown issue')}",
                    level=payload.get("level", "error"),
                    metadata=payload,
                )

            return web.json_response({"status": "processed"})

        except Exception as e:
            self.logger.exception(f"Health webhook processing failed: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_security_webhook(self, request: web.Request) -> web.Response:
        """Handle security webhook events."""
        try:
            payload = await request.json()
            event_type = payload.get("event_type", "security")

            self.logger.info(f"Received security webhook: {event_type}")

            await self.emit_event(f"webhook.security.{event_type}", payload)

            # Send immediate notification for security events
            await self.send_notification(
                f"Security alert: {payload.get('message', 'Security event detected')}",
                level="critical",
                metadata=payload,
            )

            return web.json_response({"status": "processed"})

        except Exception as e:
            self.logger.exception(f"Security webhook processing failed: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_health_check(self, request: web.Request) -> web.Response:
        """Handle health check requests."""
        return web.json_response(
            {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "webhook-manager",
            },
        )

    async def _handle_status_check(self, request: web.Request) -> web.Response:
        """Handle status check requests."""
        return web.json_response(
            {
                "service": "webhook-manager",
                "status": "running",
                "timestamp": datetime.now().isoformat(),
                "endpoints": list(self.webhook_config.get("endpoints", {}).values()),
                "registered_handlers": {
                    event_type: len(handlers)
                    for event_type, handlers in self.event_handlers.items()
                },
                "notification_endpoints": len(self.notification_endpoints),
            },
        )

    # Event processing handlers
    async def _handle_github_push(self, payload: dict[str, Any]) -> None:
        """Process GitHub push events."""
        repository = payload.get("repository", {}).get("name", "unknown")
        branch = payload.get("ref", "").replace("refs/heads/", "")
        commits = len(payload.get("commits", []))

        self.logger.info(f"GitHub push to {repository}:{branch} ({commits} commits)")

        await self.emit_event(
            "git.push",
            {
                "provider": "github",
                "repository": repository,
                "branch": branch,
                "commits": commits,
                "payload": payload,
            },
        )

    async def _handle_github_pull_request(self, payload: dict[str, Any]) -> None:
        """Process GitHub pull request events."""
        action = payload.get("action", "unknown")
        pr_number = payload.get("number", 0)
        repository = payload.get("repository", {}).get("name", "unknown")

        self.logger.info(f"GitHub PR {action}: {repository}#{pr_number}")

        await self.emit_event(
            "git.pull_request",
            {
                "provider": "github",
                "action": action,
                "repository": repository,
                "pr_number": pr_number,
                "payload": payload,
            },
        )

    async def _handle_github_release(self, payload: dict[str, Any]) -> None:
        """Process GitHub release events."""
        action = payload.get("action", "unknown")
        tag_name = payload.get("release", {}).get("tag_name", "unknown")
        repository = payload.get("repository", {}).get("name", "unknown")

        self.logger.info(f"GitHub release {action}: {repository} {tag_name}")

        await self.emit_event(
            "git.release",
            {
                "provider": "github",
                "action": action,
                "repository": repository,
                "tag": tag_name,
                "payload": payload,
            },
        )

    async def _handle_gitlab_push(self, payload: dict[str, Any]) -> None:
        """Process GitLab push events."""
        repository = payload.get("project", {}).get("name", "unknown")
        branch = payload.get("ref", "").replace("refs/heads/", "")
        commits = len(payload.get("commits", []))

        self.logger.info(f"GitLab push to {repository}:{branch} ({commits} commits)")

        await self.emit_event(
            "git.push",
            {
                "provider": "gitlab",
                "repository": repository,
                "branch": branch,
                "commits": commits,
                "payload": payload,
            },
        )

    async def _handle_gitlab_merge_request(self, payload: dict[str, Any]) -> None:
        """Process GitLab merge request events."""
        action = payload.get("object_attributes", {}).get("action", "unknown")
        mr_id = payload.get("object_attributes", {}).get("iid", 0)
        repository = payload.get("project", {}).get("name", "unknown")

        self.logger.info(f"GitLab MR {action}: {repository}!{mr_id}")

        await self.emit_event(
            "git.merge_request",
            {
                "provider": "gitlab",
                "action": action,
                "repository": repository,
                "mr_id": mr_id,
                "payload": payload,
            },
        )

    async def _handle_gitlab_pipeline(self, payload: dict[str, Any]) -> None:
        """Process GitLab pipeline events."""
        status = payload.get("object_attributes", {}).get("status", "unknown")
        pipeline_id = payload.get("object_attributes", {}).get("id", 0)
        repository = payload.get("project", {}).get("name", "unknown")

        self.logger.info(f"GitLab pipeline {status}: {repository} #{pipeline_id}")

        await self.emit_event(
            "ci.pipeline",
            {
                "provider": "gitlab",
                "status": status,
                "repository": repository,
                "pipeline_id": pipeline_id,
                "payload": payload,
            },
        )

    def add_notification_endpoint(self, endpoint_config: dict[str, Any]) -> None:
        """Add notification endpoint.

        Args:
            endpoint_config: Endpoint configuration dictionary
        """
        self.notification_endpoints.append(endpoint_config)
        self.logger.info(f"Added notification endpoint: {endpoint_config.get('name', 'unnamed')}")

    def get_webhook_url(self, endpoint_name: str) -> str | None:
        """Get webhook URL for endpoint.

        Args:
            endpoint_name: Name of webhook endpoint

        Returns:
            Full webhook URL or None if not found
        """
        endpoint_path = self.webhook_config.get("endpoints", {}).get(endpoint_name)
        if not endpoint_path:
            return None

        host = self.webhook_config.get("host", "localhost")
        port = self.webhook_config.get("port", 8080)

        # Use localhost if bound to 0.0.0.0
        if host == "0.0.0.0":
            host = "localhost"

        return f"http://{host}:{port}{endpoint_path}"
