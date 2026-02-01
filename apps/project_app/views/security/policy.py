"""
Security policy views for SciTeX projects
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.project_app.models import Project

# TODO: Fix when security models are properly structured
# from apps.project_app.models.security import SecurityPolicy

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET", "POST"])
def security_policy(request, username, slug):
    """
    View and edit security policy (SECURITY.md)
    """
    project = get_object_or_404(Project, slug=slug, owner__username=username)

    # Check permissions
    if not project.can_edit(request.user):
        return HttpResponseForbidden("You don't have permission to edit this project")

    # Get or create security policy
    policy, created = SecurityPolicy.objects.get_or_create(
        project=project, defaults={"created_by": request.user}
    )

    if request.method == "POST":
        # Update policy
        policy.content = request.POST.get("content", "")
        policy.contact_email = request.POST.get("contact_email", "")
        policy.contact_url = request.POST.get("contact_url", "")
        policy.save()

        # Save to SECURITY.md file
        try:
            policy.save_to_file()
            messages.success(request, "Security policy updated successfully")
        except Exception as e:
            logger.error(f"Failed to save SECURITY.md: {e}")
            messages.error(request, "Failed to save SECURITY.md file")

        return redirect("user_projects:security_policy", username=username, slug=slug)

    context = {
        "project": project,
        "policy": policy,
        "created": created,
        "can_edit": project.can_edit(request.user),
    }

    return render(request, "project_app/security/policy.html", context)
