#!/usr/bin/env python3
"""
GitHub Webhook Integration for GitOps Automated Deployments
Triggers ArgoCD sync when repository changes are detected.
"""

import hashlib
import hmac
import logging
import os
import subprocess
from datetime import datetime

from flask import Flask, abort, jsonify, request

from kubernetes import client, config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "your-github-webhook-secret")
ARGOCD_SERVER = os.environ.get("ARGOCD_SERVER", "argocd-server.argocd.svc.cluster.local:443")
ARGOCD_TOKEN = os.environ.get("ARGOCD_TOKEN", "")
NAMESPACE = os.environ.get("NAMESPACE", "argocd")

# Load Kubernetes config
try:
    config.load_incluster_config()
    logger.info("Loaded in-cluster Kubernetes configuration")
except config.ConfigException:
    config.load_kube_config()
    logger.info("Loaded local Kubernetes configuration")

k8s_client = client.ApiClient()


def verify_signature(payload_body, signature_header):
    """Verify GitHub webhook signature."""
    if not signature_header:
        logger.warning("No signature header provided")
        return False

    sha_name, signature = signature_header.split("=")
    if sha_name != "sha256":
        logger.warning(f"Unsupported signature type: {sha_name}")
        return False

    mac = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    )

    return hmac.compare_digest(mac.hexdigest(), signature)


def trigger_argocd_sync(application_name, repository_url, branch="main"):
    """Trigger ArgoCD application sync."""
    try:
        cmd = [
            "argocd",
            "app",
            "sync",
            application_name,
            "--server",
            ARGOCD_SERVER,
            "--auth-token",
            ARGOCD_TOKEN,
            "--grpc-web",
            "--prune",
            "--force",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )

        if result.returncode == 0:
            logger.info(f"Successfully synced application: {application_name}")
            return {
                "status": "success",
                "message": f"Application {application_name} synced successfully",
                "output": result.stdout,
            }
        logger.error(f"Failed to sync application {application_name}: {result.stderr}")
        return {
            "status": "error",
            "message": f"Failed to sync application {application_name}",
            "error": result.stderr,
        }

    except subprocess.TimeoutExpired:
        logger.exception(f"Timeout syncing application: {application_name}")
        return {
            "status": "error",
            "message": f"Timeout syncing application {application_name}",
        }
    except Exception as e:
        logger.exception(f"Exception syncing application {application_name}: {e!s}")
        return {
            "status": "error",
            "message": f"Exception syncing application {application_name}",
            "error": str(e),
        }


def get_affected_applications(repository_url, changed_files):
    """Determine which ArgoCD applications are affected by changes."""
    affected_apps = []

    # Application path mappings
    app_mappings = {
        "deployments/gitops/applications/infrastructure.yaml": [
            "metallb",
            "cert-manager",
            "ingress-nginx",
            "longhorn",
        ],
        "deployments/gitops/applications/monitoring.yaml": ["prometheus-stack", "loki-stack"],
        "deployments/gitops/overlays/development/": ["homelab-apps"],
        "deployments/gitops/overlays/staging/": ["homelab-apps"],
        "deployments/gitops/overlays/production/": ["homelab-apps"],
        "helm/": ["homelab-apps"],
        "kubernetes/": ["homelab-apps"],
    }

    for file_path in changed_files:
        for pattern, apps in app_mappings.items():
            if file_path.startswith(pattern):
                affected_apps.extend(apps)

    # Remove duplicates and return
    return list(set(affected_apps))


@app.route("/webhook/github", methods=["POST"])
def github_webhook():
    """Handle GitHub webhook events."""
    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(request.data, signature):
        logger.warning("Invalid webhook signature")
        abort(401)

    # Parse payload
    payload = request.get_json()
    if not payload:
        logger.warning("No JSON payload received")
        abort(400)

    event_type = request.headers.get("X-GitHub-Event")
    logger.info(f"Received GitHub webhook event: {event_type}")

    # Handle push events
    if event_type == "push":
        repository_url = payload["repository"]["clone_url"]
        branch = payload["ref"].split("/")[-1]
        commits = payload["commits"]

        # Get changed files
        changed_files = []
        for commit in commits:
            changed_files.extend(commit.get("added", []))
            changed_files.extend(commit.get("modified", []))
            changed_files.extend(commit.get("removed", []))

        logger.info(f"Push to {repository_url}:{branch} with {len(changed_files)} changed files")

        # Determine affected applications
        affected_apps = get_affected_applications(repository_url, changed_files)

        if not affected_apps:
            logger.info("No applications affected by changes")
            return jsonify(
                {
                    "status": "success",
                    "message": "No applications affected by changes",
                }
            )

        # Trigger sync for affected applications
        sync_results = []
        for app in affected_apps:
            result = trigger_argocd_sync(app, repository_url, branch)
            sync_results.append(
                {
                    "application": app,
                    "result": result,
                }
            )

        return jsonify(
            {
                "status": "success",
                "message": f"Processed push event for {len(affected_apps)} applications",
                "affected_applications": affected_apps,
                "sync_results": sync_results,
            }
        )

    # Handle pull request events
    if event_type == "pull_request":
        action = payload["action"]
        pr_number = payload["number"]

        if action in ["opened", "synchronize", "reopened"]:
            logger.info(f"Pull request #{pr_number} {action}")

            # For PR events, we might want to trigger a different workflow
            # such as creating a preview environment or running validation

            return jsonify(
                {
                    "status": "success",
                    "message": f"Pull request #{pr_number} {action} - validation triggered",
                }
            )
        return None

    # Handle other events
    logger.info(f"Ignoring event type: {event_type}")
    return jsonify(
        {
            "status": "ignored",
            "message": f"Event type {event_type} not processed",
        }
    )


@app.route("/webhook/drift", methods=["POST"])
def drift_notification():
    """Handle drift detection notifications."""
    payload = request.get_json()

    if not payload:
        abort(400)

    logger.warning(f"Drift detected in application: {payload.get('application')}")

    # Here you could integrate with alerting systems
    # Slack, email, PagerDuty, etc.

    return jsonify(
        {
            "status": "received",
            "message": "Drift notification processed",
        }
    )


@app.route("/webhook/health", methods=["POST"])
def health_notification():
    """Handle health status notifications."""
    payload = request.get_json()

    if not payload:
        abort(400)

    logger.warning(
        f"Health issue in application: {payload.get('application')} - {payload.get('health')}"
    )

    return jsonify(
        {
            "status": "received",
            "message": "Health notification processed",
        }
    )


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
        }
    )


if __name__ == "__main__":
    logger.info("Starting GitOps webhook service")
    app.run(host="0.0.0.0", port=8080, debug=False)
