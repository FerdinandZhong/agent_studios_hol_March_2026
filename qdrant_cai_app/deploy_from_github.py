#!/usr/bin/env python3
"""
Deploy Qdrant to Cloudera AI from GitHub Actions.

Creates a CML project (with git sync) and launches the Qdrant application.

Environment Variables:
    CML_HOST: CML workspace URL (required)
    CML_API_KEY: CML API key (required)
    GH_PAT: GitHub PAT for git sync (optional)
    GITHUB_REPOSITORY: GitHub repo in owner/repo format (optional)
"""

import os
import sys
import time
import requests
from typing import Optional

# Configuration (shared with deploy_qdrant.py)
PROJECT_NAME = "qdrant-server"
APP_NAME = "Qdrant Vector DB"
APP_SCRIPT = "qdrant_cai_app/run_qdrant.py"
RUNTIME_IMAGE = "docker.repository.cloudera.com/cloudera/cdsw/ml-runtime-pbj-jupyterlab-python3.11-standard:2026.01.1-b6"


def make_request(session: requests.Session, method: str, url: str, **kwargs) -> Optional[dict]:
    """Make API request and return JSON response or None on error."""
    response = session.request(method, url, **kwargs)
    print(f"  {method} {url} -> {response.status_code}")

    if 200 <= response.status_code < 300:
        return response.json() if response.text else {}

    print(f"  Error: {response.text[:500]}")
    return None


def find_project(session: requests.Session, api_url: str) -> Optional[str]:
    """Find existing project by name."""
    result = make_request(
        session, "GET", f"{api_url}/projects",
        params={"search_filter": f'{{"name":"{PROJECT_NAME}"}}', "page_size": 50}
    )
    if result:
        for project in result.get("projects", []):
            if project.get("name") == PROJECT_NAME:
                return project.get("id")
    return None


def create_project(session: requests.Session, api_url: str) -> Optional[str]:
    """Create new project with git sync."""
    github_token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
    github_repo = os.environ.get("GITHUB_REPOSITORY", "")

    project_data = {
        "name": PROJECT_NAME,
        "description": "Qdrant Vector Database Server",
        "visibility": "private",
        "template": "git",
    }

    if github_token and github_repo:
        print(f"  Configuring git sync: {github_repo}")
        project_data["git_url"] = f"https://{github_token}@github.com/{github_repo}.git"

    result = make_request(session, "POST", f"{api_url}/projects", json=project_data)
    return result.get("id") if result else None


def wait_for_project_ready(session: requests.Session, api_url: str, project_id: str, timeout: int = 300) -> bool:
    """Wait for project git clone to complete."""
    print(f"Waiting for project to be ready (timeout: {timeout}s)...")
    start = time.time()

    while (time.time() - start) < timeout:
        result = make_request(session, "GET", f"{api_url}/projects/{project_id}")
        if result:
            status = result.get("creation_status", "unknown")
            elapsed = int(time.time() - start)
            print(f"  [{elapsed}s] Status: {status}")

            if status == "error":
                return False
            if status in ("success", "ready", "running"):
                time.sleep(10)
                return True

        time.sleep(10)

    print("  Timeout waiting for project")
    return False


def deploy_application(session: requests.Session, api_url: str, project_id: str) -> Optional[str]:
    """Create or update the Qdrant application."""
    subdomain = f"qdrant-{project_id.lower()}"
    apps_url = f"{api_url}/projects/{project_id}/applications"

    app_config = {
        "name": APP_NAME,
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

    result = make_request(session, "GET", apps_url)
    existing_app_id = None
    if result:
        for app in result.get("applications", []):
            if app.get("name") == APP_NAME:
                existing_app_id = app.get("id")
                break

    if existing_app_id:
        print(f"Updating existing application: {existing_app_id}")
        result = make_request(session, "PATCH", f"{apps_url}/{existing_app_id}", json=app_config)
        if result is not None:
            make_request(session, "POST", f"{apps_url}/{existing_app_id}/restart")
            return existing_app_id
    else:
        print("Creating new application...")
        result = make_request(session, "POST", apps_url, json=app_config)
        if result:
            return result.get("id")

    return None


def main():
    print("=" * 60)
    print("  Deploy Qdrant to Cloudera AI (GitHub Actions)")
    print("=" * 60)
    print()

    cml_host = os.environ.get("CML_HOST")
    api_key = os.environ.get("CML_API_KEY")

    if not cml_host or not api_key:
        print("Error: CML_HOST and CML_API_KEY environment variables required")
        sys.exit(1)

    api_url = f"{cml_host.rstrip('/')}/api/v2"
    print(f"CML Host: {cml_host}")
    print(f"Project: {PROJECT_NAME}")
    print()

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    })

    # Get or create project
    print("Checking for existing project...")
    project_id = find_project(session, api_url)
    needs_wait = False

    if not project_id:
        print("Creating new project...")
        project_id = create_project(session, api_url)
        if not project_id:
            print("Failed to create project")
            sys.exit(1)
        needs_wait = True

    print(f"Project ID: {project_id}")

    if needs_wait:
        if not wait_for_project_ready(session, api_url, project_id):
            print("Project setup failed")
            sys.exit(1)

    print()
    print("Deploying Qdrant application...")
    app_id = deploy_application(session, api_url, project_id)

    if not app_id:
        print("Failed to deploy application")
        sys.exit(1)

    print()
    print("=" * 60)
    print("  Deployment Complete!")
    print("=" * 60)
    print()
    print(f"Application ID: {app_id}")
    print(f"URL: {cml_host}/qdrant-{project_id.lower()}")
    print()


if __name__ == "__main__":
    main()
