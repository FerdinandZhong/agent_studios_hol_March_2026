#!/usr/bin/env python3
"""
Deploy Qdrant as a CAI Application.

Run this script as a CAI Job to create/update the Qdrant application.

Environment variables:
  - CDSW_* : Auto-set when running inside CAI
  - app_suffix : Optional suffix for app name (e.g., "user1" -> "Qdrant Vector DB - user1")
                 Allows multiple users to deploy concurrently with unique app names
"""

import os
import sys
import requests

# Configuration
BASE_APP_NAME = "Qdrant Vector DB"
APP_SCRIPT = "qdrant_cai_app/run_qdrant.py"
RUNTIME_IMAGE = "docker.repository.cloudera.com/cloudera/cdsw/ml-runtime-pbj-jupyterlab-python3.11-standard:2026.01.1-b6"


def get_app_name() -> str:
    """Get application name with optional suffix from environment variable."""
    suffix = os.environ.get("app_suffix", "").strip()
    if suffix:
        return f"{BASE_APP_NAME} - {suffix}"
    return BASE_APP_NAME


def get_subdomain(project_id: str) -> str:
    """Get subdomain with optional suffix from environment variable."""
    suffix = os.environ.get("app_suffix", "").strip()
    if suffix:
        return f"qdrant-{suffix.lower()}-{project_id.lower()}"
    return f"qdrant-{project_id.lower()}"


def deploy_application(client: requests.Session, domain: str, project_id: str) -> dict:
    """Create or update CAI Application for Qdrant."""
    app_name = get_app_name()
    subdomain = get_subdomain(project_id)
    apps_url = f"{domain}/api/v2/projects/{project_id}/applications"

    app_config = {
        "name": app_name,
        "description": "Qdrant Vector Database Server",
        "subdomain": subdomain,
        "script": APP_SCRIPT,
        "kernel": "python3",
        "cpu": 2,
        "memory": 8,
        "bypass_authentication": False,
        "runtime_identifier": RUNTIME_IMAGE,
        "environment": {"QDRANT_DATA_PATH": "/home/cdsw/qdrant_data"}
    }

    # Check for existing application
    response = client.get(apps_url)
    response.raise_for_status()

    existing_app = None
    for app in response.json().get("applications", []):
        if app.get("name") == app_name:
            existing_app = app
            break

    if existing_app:
        app_id = existing_app["id"]
        print(f"Updating existing application: {app_id}")
        client.patch(f"{apps_url}/{app_id}", json=app_config).raise_for_status()
        client.post(f"{apps_url}/{app_id}/restart").raise_for_status()
        print("Application updated and restarted")
        return existing_app

    print("Creating new application...")
    response = client.post(apps_url, json=app_config)
    response.raise_for_status()
    created_app = response.json()
    print(f"Application created: {created_app.get('id')}")
    return created_app


def main():
    print("=" * 60)
    print("  Deploy Qdrant as CAI Application")
    print("=" * 60)
    print()

    # Get credentials from CAI environment
    api_key = os.environ.get("CDSW_APIV2_KEY")
    domain = os.environ.get("CDSW_DOMAIN")
    project_id = os.environ.get("CDSW_PROJECT_ID")

    if not all([api_key, domain, project_id]):
        print("Error: Must run inside CAI (CDSW_APIV2_KEY, CDSW_DOMAIN, CDSW_PROJECT_ID required)")
        sys.exit(1)

    if not domain.startswith(("http://", "https://")):
        domain = f"https://{domain}"

    app_name = get_app_name()
    subdomain = get_subdomain(project_id)

    print(f"Domain: {domain}")
    print(f"Project ID: {project_id}")
    print(f"App Name: {app_name}")
    print(f"Subdomain: {subdomain}")
    print()

    client = requests.Session()
    client.headers.update({
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    })

    try:
        deploy_application(client, domain, project_id)

        print()
        print("=" * 60)
        print("  Deployment Complete!")
        print("=" * 60)
        print()
        print(f"Application URL: {domain}/{subdomain}")
        print("Status: Starting (wait 1-2 minutes)")
        print()

    except requests.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
