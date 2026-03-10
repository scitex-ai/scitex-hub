"""
Security Feature URLs

Handles all security-related URLs.
GitHub-style patterns:
- /<username>/<slug>/security/ - Security overview
- /<username>/<slug>/security/alerts/ - Security alerts
- /<username>/<slug>/security/policy/ - Security policy
- /<username>/<slug>/security/advisories/ - Security advisories
- /<username>/<slug>/security/dependabot/ - Dependency graph
"""

from django.urls import path

from ..views.security import (
    api_dependency_tree,
    create_fix_pr,
    dependency_graph,
    dismiss_alert,
    reopen_alert,
    scan_history,
    security_advisories,
    security_alert_detail,
    security_alerts,
    security_overview,
    security_policy_edit,
    trigger_security_scan,
)

# No app_name here - namespace is provided by parent (project_app)

urlpatterns = [
    # Security overview
    path("", security_overview, name="overview"),
    # Security alerts
    path("alerts/", security_alerts, name="alerts"),
    path("alerts/<int:alert_id>/", security_alert_detail, name="alert_detail"),
    # Security policy
    path("policy/", security_policy_edit, name="policy"),
    # Security advisories
    path("advisories/", security_advisories, name="advisories"),
    # Dependency graph
    path("dependabot/", dependency_graph, name="dependency_graph"),
    # Scan history
    path("scans/", scan_history, name="scan_history"),
    # Security API endpoints
    path("api/scan/", trigger_security_scan, name="api_trigger_scan"),
    path("api/alerts/<int:alert_id>/dismiss/", dismiss_alert, name="api_dismiss_alert"),
    path("api/alerts/<int:alert_id>/reopen/", reopen_alert, name="api_reopen_alert"),
    path("api/alerts/<int:alert_id>/fix/", create_fix_pr, name="api_create_fix_pr"),
    path(
        "api/dependencies/<int:dependency_id>/tree/",
        api_dependency_tree,
        name="api_dependency_tree",
    ),
]
