"""
Security alerts views for SciTeX projects
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from apps.project_app.models import Project

# TODO: Fix when security models are properly structured
# from apps.project_app.models.security import SecurityAlert

logger = logging.getLogger(__name__)


@login_required
def security_alerts(request, username, slug):
    """
    List all security alerts with filtering
    """
    project = get_object_or_404(Project, slug=slug, owner__username=username)

    # Check permissions
    if not project.can_view(request.user):
        return HttpResponseForbidden("You don't have permission to view this project")

    # Get filter parameters
    status_filter = request.GET.get("status", "open")
    severity_filter = request.GET.get("severity", "all")
    alert_type_filter = request.GET.get("type", "all")

    # Build query
    alerts = SecurityAlert.objects.filter(project=project)

    if status_filter and status_filter != "all":
        alerts = alerts.filter(status=status_filter)

    if severity_filter and severity_filter != "all":
        alerts = alerts.filter(severity=severity_filter)

    if alert_type_filter and alert_type_filter != "all":
        alerts = alerts.filter(alert_type=alert_type_filter)

    # Order by severity and date
    alerts = alerts.order_by("-severity", "-created_at")

    # Pagination
    paginator = Paginator(alerts, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "project": project,
        "page_obj": page_obj,
        "status_filter": status_filter,
        "severity_filter": severity_filter,
        "alert_type_filter": alert_type_filter,
    }

    return render(request, "project_app/security/alerts.html", context)


@login_required
def security_alert_detail(request, username, slug, alert_id):
    """
    Display details of a single security alert
    """
    project = get_object_or_404(Project, slug=slug, owner__username=username)
    alert = get_object_or_404(SecurityAlert, id=alert_id, project=project)

    # Check permissions
    if not project.can_view(request.user):
        return HttpResponseForbidden("You don't have permission to view this project")

    context = {
        "project": project,
        "alert": alert,
        "can_edit": project.can_edit(request.user),
    }

    return render(request, "project_app/security/alert_detail.html", context)


@login_required
@require_http_methods(["POST"])
def dismiss_alert(request, username, slug, alert_id):
    """
    Dismiss a security alert
    """
    project = get_object_or_404(Project, slug=slug, owner__username=username)
    alert = get_object_or_404(SecurityAlert, id=alert_id, project=project)

    # Check permissions
    if not project.can_edit(request.user):
        return JsonResponse({"error": "Permission denied"}, status=403)

    reason = request.POST.get("reason", "")
    alert.dismiss(user=request.user, reason=reason)

    messages.success(request, "Alert dismissed successfully")

    return JsonResponse(
        {
            "success": True,
            "alert_id": alert.id,
            "status": alert.status,
        }
    )


@login_required
@require_http_methods(["POST"])
def reopen_alert(request, username, slug, alert_id):
    """
    Reopen a dismissed alert
    """
    project = get_object_or_404(Project, slug=slug, owner__username=username)
    alert = get_object_or_404(SecurityAlert, id=alert_id, project=project)

    # Check permissions
    if not project.can_edit(request.user):
        return JsonResponse({"error": "Permission denied"}, status=403)

    alert.status = "open"
    alert.dismissed_at = None
    alert.dismissed_by = None
    alert.dismissed_reason = ""
    alert.save()

    messages.success(request, "Alert reopened successfully")

    return JsonResponse(
        {
            "success": True,
            "alert_id": alert.id,
            "status": alert.status,
        }
    )


@login_required
@require_http_methods(["POST"])
def create_fix_pr(request, username, slug, alert_id):
    """
    Create a pull request to fix a vulnerability
    This would integrate with Gitea to create a PR
    """
    project = get_object_or_404(Project, slug=slug, owner__username=username)
    alert = get_object_or_404(SecurityAlert, id=alert_id, project=project)

    # Check permissions
    if not project.can_edit(request.user):
        return JsonResponse({"error": "Permission denied"}, status=403)

    if not alert.fix_available:
        return JsonResponse({"error": "No automatic fix available"}, status=400)

    try:
        # This is a placeholder for actual PR creation logic
        # Would need to:
        # 1. Create a new branch
        # 2. Update requirements.txt with fixed version
        # 3. Commit changes
        # 4. Create PR via Gitea API

        messages.info(request, "Automatic fix PR creation is not yet implemented")

        return JsonResponse(
            {
                "success": False,
                "error": "Feature not yet implemented",
            }
        )

    except Exception as e:
        logger.error(f"Failed to create fix PR: {e}")
        return JsonResponse({"error": str(e)}, status=500)
