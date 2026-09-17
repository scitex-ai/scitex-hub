"""
Collaboration Views
Handles project invitations, members, and permissions.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from apps.infra.project_app.models import Project, ProjectInvitation

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


def _invite_response(callable_, kwargs: dict, status: int | None = None):
    """Apply the invite route's response hygiene in one place.

    no-store:    the page names a project for one person; do not cache it.
    noindex:     an invitation URL must never be indexed or followed.
    no-referrer: the token is in the URL, and the shell loads third-party assets
                 (fonts, icon CDN), so without this the token rides along in the
                 Referer header to origins that have no business seeing it.
    """
    if "request" in kwargs:
        response = callable_(**kwargs)
    else:
        response = callable_(kwargs["redirect_to"], status=status or 303)
    response["Cache-Control"] = "no-store"
    response["X-Robots-Tag"] = "noindex, nofollow"
    response["Referrer-Policy"] = "no-referrer"
    return response


def _invitation_state(invitation, is_recipient: bool) -> str:
    """Which honest state the invitation is in, from the recipient's point of view.

    ``not_yours`` comes first and deliberately: a stranger holding someone else's
    link must not learn whether it is pending, expired or already answered.
    """
    if not is_recipient:
        return "not_yours"
    if invitation.status == "accepted":
        return "already_accepted"
    if invitation.status == "declined":
        return "already_declined"
    if invitation.is_expired():
        return "expired"
    return "review"


@login_required
def accept_invitation(request, token):
    """Review first, then accept — never join just because a link was opened.

    Card: hub-project-collaboration-invite-links-20260917. SSOT §9: "A recipient
    signs in or creates and verifies their own SciTeX account, reviews the project
    and role, then explicitly accepts. Opening the link or completing signup does
    not silently join the project."

    This used to accept on GET, so a single page load created the membership and
    dropped the recipient inside the project: a prefetch, a link scanner or a
    mis-click joined on their behalf. GET now renders the review; only POST accepts.
    """
    invitation = get_object_or_404(ProjectInvitation, token=token)
    is_recipient = invitation.invited_user_id == request.user.id

    if request.method == "POST":
        if not is_recipient:
            messages.error(request, "This invitation is not for you")
            return _invite_response(redirect, {"redirect_to": "/"})
        if invitation.is_expired():
            messages.error(request, "This invitation has expired")
            return _invite_response(redirect, {"redirect_to": "/"})
        if invitation.accept():
            messages.success(
                request, f"You're now a collaborator on {invitation.project.name}!"
            )
            target = f"/{invitation.project.owner.username}/{invitation.project.slug}/"
            return _invite_response(redirect, {"redirect_to": target})
        messages.error(request, "Invitation has already been responded to")
        return _invite_response(redirect, {"redirect_to": "/"})

    state = _invitation_state(invitation, is_recipient)
    context = {"state": state, "token": token}
    if is_recipient:
        # Only the named recipient sees what is on offer, and only what they need
        # to decide: no files, no activity, no member list before they accept.
        context.update(
            {
                "project_name": invitation.project.name,
                "inviter_name": invitation.invited_by.username,
                "role": invitation.get_role_display(),
                "permission_level": invitation.get_permission_level_display(),
                "expires_at": invitation.expires_at,
                "accept_url": f"/invitations/{token}/accept/",
                "decline_url": f"/invitations/{token}/decline/",
            }
        )
    return _invite_response(
        render,
        {
            "request": request,
            "template_name": "project_app/invitation_review.html",
            "context": context,
        },
    )


@login_required
def decline_invitation(request, token):
    """Decline an invitation (POST only — declining is a state change too)."""
    invitation = get_object_or_404(ProjectInvitation, token=token)

    if invitation.invited_user_id != request.user.id:
        messages.error(request, "This invitation is not for you")
        return _invite_response(redirect, {"redirect_to": "/"})

    if request.method != "POST":
        return _invite_response(
            redirect, {"redirect_to": f"/invitations/{token}/accept/"}
        )

    if invitation.decline():
        messages.success(request, f"Invitation to {invitation.project.name} declined")
    else:
        messages.error(request, "Invitation has already been responded to")

    return _invite_response(redirect, {"redirect_to": "/"})


# EOF
