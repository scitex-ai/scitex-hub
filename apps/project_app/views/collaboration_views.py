"""
Collaboration Views
Handles project invitations, members, and permissions.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from apps.project_app.models import Project, ProjectInvitation
import logging

logger = logging.getLogger(__name__)


@login_required
def project_collaborate(request, username, slug):
    """Project collaboration management - redirects to settings with collaborators tab"""
    # Redirect to main settings page with collaborators section
    return redirect(f"/{username}/{slug}/settings/#collaborators")


@login_required
def project_members(request, username, slug):
    """Project members management"""
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Only project owner can manage members
    if project.owner != request.user:
        messages.error(
            request,
            "You don't have permission to manage members for this project.",
        )
        return redirect("project_app:detail", username=username, slug=slug)

    context = {
        "project": project,
        "members": project.memberships.all(),
    }
    return render(request, "project_app/project_members.html", context)


@login_required
def accept_invitation(request, token):
    """Accept a project collaboration invitation."""
    try:
        invitation = get_object_or_404(ProjectInvitation, token=token)

        # Check if invitation is for current user
        if invitation.invited_user != request.user:
            messages.error(request, "This invitation is not for you")
            return redirect("/")

        # Check if expired
        if invitation.is_expired():
            messages.error(request, "This invitation has expired")
            return redirect("/")

        # Accept invitation
        if invitation.accept():
            messages.success(
                request, f"You're now a collaborator on {invitation.project.name}!"
            )
            # Redirect to project
            return redirect(
                f"/{invitation.project.owner.username}/{invitation.project.slug}/"
            )
        else:
            messages.error(request, "Invitation has already been responded to")
            return redirect("/")

    except Exception as e:
        logger.error(f"Error accepting invitation: {e}")
        messages.error(request, "Error accepting invitation")
        return redirect("/")


@login_required
def decline_invitation(request, token):
    """Decline a project collaboration invitation."""
    try:
        invitation = get_object_or_404(ProjectInvitation, token=token)

        # Check if invitation is for current user
        if invitation.invited_user != request.user:
            messages.error(request, "This invitation is not for you")
            return redirect("/")

        # Decline invitation
        if invitation.decline():
            messages.success(
                request, f"Invitation to {invitation.project.name} declined"
            )
        else:
            messages.error(request, "Invitation has already been responded to")

        return redirect("/")

    except Exception as e:
        logger.error(f"Error declining invitation: {e}")
        messages.error(request, "Error declining invitation")
        return redirect("/")


# EOF
