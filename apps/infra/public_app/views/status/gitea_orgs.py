"""
Gitea Organisation Health Checks

Verifies that required Gitea organisations (scitex, scitex-apps) exist
and have corresponding Django Organisation records.
"""

import logging

logger = logging.getLogger("scitex")

REQUIRED_ORGS = [
    ("scitex", "App registry (MELPA-style metadata)"),
    ("scitex-apps", "Published app forks"),
]


def check_gitea_orgs(status_data):
    """Check that required Gitea organisations exist."""
    status_data["gitea_orgs"] = []

    for org_name, description in REQUIRED_ORGS:
        entry = {
            "name": org_name,
            "description": description,
            "is_running": False,
            "status": "missing",
            "health_class": "unhealthy",
        }

        # Check Gitea org
        try:
            from apps.infra.gitea_app.api_client import GiteaClient

            client = GiteaClient()
            data = client.get_organization(org_name)
            entry.update(
                {
                    "is_running": True,
                    "status": "exists",
                    "health_class": "healthy",
                    "details": data.get("full_name", org_name),
                }
            )
        except Exception as e:
            entry["error"] = str(e)

        # Check Django Organisation record
        try:
            from apps.infra.organizations_app.models import Organization

            entry["django_record"] = Organization.objects.filter(slug=org_name).exists()
            if not entry["django_record"] and entry["health_class"] == "healthy":
                entry["health_class"] = "warning"
                entry["status"] = "gitea-only"
                entry["details"] = entry.get("details", "") + " (Django record missing)"
        except Exception:
            entry["django_record"] = None

        status_data["gitea_orgs"].append(entry)
