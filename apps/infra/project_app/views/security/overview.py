"""
Security overview view for SciTeX projects
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
import logging

from apps.infra.project_app.models import Project

# TODO: Fix when security models are properly structured
# from apps.infra.project_app.models.security import (
#     SecurityAlert,
#     SecurityPolicy,
#     SecurityAdvisory,
#     DependencyGraph,
#     SecurityScanResult,
# )

logger = logging.getLogger(__name__)


@login_required
def security_overview(request, username, slug):
    """
    Security overview dashboard
    Shows summary of security status and recent alerts
    """
    project = get_object_or_404(Project, slug=slug, owner__username=username)

    # Check permissions
    if not project.can_view(request.user):
        return HttpResponseForbidden("You don't have permission to view this project")

    # Get security statistics
    alerts = SecurityAlert.objects.filter(project=project)
    open_alerts = alerts.filter(status="open")

    stats = {
        "total_alerts": alerts.count(),
        "open_alerts": open_alerts.count(),
        "critical": open_alerts.filter(severity="critical").count(),
        "high": open_alerts.filter(severity="high").count(),
        "medium": open_alerts.filter(severity="medium").count(),
        "low": open_alerts.filter(severity="low").count(),
        "fixed": alerts.filter(status="fixed").count(),
        "dismissed": alerts.filter(status="dismissed").count(),
    }

    # Get recent alerts
    recent_alerts = open_alerts.order_by("-created_at")[:10]

    # Get recent scans
    recent_scans = SecurityScanResult.objects.filter(project=project).order_by(
        "-started_at"
    )[:5]

    # Check if security policy exists
    try:
        security_policy = SecurityPolicy.objects.get(project=project)
        has_policy = True
    except SecurityPolicy.DoesNotExist:
        security_policy = None
        has_policy = False

    # Get dependency statistics
    dependencies = DependencyGraph.objects.filter(project=project)
    vulnerable_deps = dependencies.filter(has_vulnerabilities=True).count()

    context = {
        "project": project,
        "stats": stats,
        "recent_alerts": recent_alerts,
        "recent_scans": recent_scans,
        "has_policy": has_policy,
        "security_policy": security_policy,
        "total_dependencies": dependencies.count(),
        "vulnerable_dependencies": vulnerable_deps,
    }

    return render(request, "project_app/security/overview.html", context)
