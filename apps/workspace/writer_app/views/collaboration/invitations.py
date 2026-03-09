"""
API endpoints for collaboration invitations.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
import json

from ...models import Manuscript
from ...models.collaboration import CollaborationInvitation


@require_http_methods(["POST"])
@login_required
def send_invitation(request, manuscript_id):
    """
    Send collaboration invitation.

    POST /writer/api/manuscript/<id>/invite/
    Body: {
        "username": "user123" or "email": "user@example.com",
        "role": "editor",  # editor, viewer, or admin
        "message": "Optional message"
    }
    """
    try:
        data = json.loads(request.body)
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        role = data.get("role", "editor")
        message = data.get("message", "")

        # Validate
        if not username and not email:
            return JsonResponse(
                {"success": False, "error": "Username or email required"}, status=400
            )

        # Get manuscript
        manuscript = Manuscript.objects.select_related("owner", "project").get(
            id=manuscript_id
        )

        # Check permission (must be owner or admin collaborator)
        if manuscript.owner != request.user:
            return JsonResponse(
                {"success": False, "error": "Permission denied"}, status=403
            )

        # Find user
        invited_user = None
        if username:
            try:
                invited_user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse(
                    {"success": False, "error": f"User '{username}' not found"},
                    status=404,
                )

        # Check if already invited
        if invited_user:
            existing = CollaborationInvitation.objects.filter(
                manuscript=manuscript, invited_user=invited_user, status="pending"
            ).exists()
            if existing:
                return JsonResponse(
                    {"success": False, "error": "User already invited"}, status=400
                )
        elif email:
            existing = CollaborationInvitation.objects.filter(
                manuscript=manuscript, invited_email=email, status="pending"
            ).exists()
            if existing:
                return JsonResponse(
                    {"success": False, "error": "Email already invited"}, status=400
                )

        # Create invitation
        invitation = CollaborationInvitation.objects.create(
            manuscript=manuscript,
            invited_by=request.user,
            invited_user=invited_user,
            invited_email=email if not invited_user else "",
            role=role,
            message=message,
        )

        return JsonResponse(
            {
                "success": True,
                "invitation": {
                    "id": str(invitation.id),
                    "invitee": invited_user.username if invited_user else email,
                    "role": invitation.role,
                    "created_at": invitation.created_at.isoformat(),
                },
            }
        )

    except Manuscript.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Manuscript not found"}, status=404
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["GET"])
@login_required
def list_invitations(request, manuscript_id):
    """
    List all invitations for a manuscript.

    GET /writer/api/manuscript/<id>/invitations/
    """
    try:
        manuscript = Manuscript.objects.get(id=manuscript_id)

        # Check permission
        if manuscript.owner != request.user:
            return JsonResponse(
                {"success": False, "error": "Permission denied"}, status=403
            )

        invitations = CollaborationInvitation.objects.filter(
            manuscript=manuscript
        ).select_related("invited_by", "invited_user")

        return JsonResponse(
            {
                "success": True,
                "invitations": [
                    {
                        "id": str(inv.id),
                        "invitee": (
                            inv.invited_user.username
                            if inv.invited_user
                            else inv.invited_email
                        ),
                        "invited_by": inv.invited_by.username,
                        "role": inv.role,
                        "status": inv.status,
                        "created_at": inv.created_at.isoformat(),
                    }
                    for inv in invitations
                ],
            }
        )

    except Manuscript.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Manuscript not found"}, status=404
        )


@require_http_methods(["POST"])
@login_required
def respond_invitation(request, invitation_id):
    """
    Accept or decline an invitation.

    POST /writer/api/invitation/<id>/respond/
    Body: {"action": "accept" or "decline"}
    """
    try:
        data = json.loads(request.body)
        action = data.get("action")

        if action not in ["accept", "decline"]:
            return JsonResponse(
                {"success": False, "error": "Invalid action"}, status=400
            )

        invitation = CollaborationInvitation.objects.select_related(
            "manuscript", "invited_by"
        ).get(id=invitation_id)

        # Check permission (must be the invited user)
        if invitation.invited_user != request.user:
            return JsonResponse(
                {"success": False, "error": "Permission denied"}, status=403
            )

        if action == "accept":
            invitation.accept()
        else:
            invitation.decline()

        return JsonResponse({"success": True, "status": invitation.status})

    except CollaborationInvitation.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Invitation not found"}, status=404
        )


@require_http_methods(["POST"])
@login_required
def cancel_invitation(request, invitation_id):
    """
    Cancel an invitation (by inviter).

    POST /writer/api/invitation/<id>/cancel/
    """
    try:
        invitation = CollaborationInvitation.objects.select_related("manuscript").get(
            id=invitation_id
        )

        # Check permission (must be the inviter or manuscript owner)
        if (
            invitation.invited_by != request.user
            and invitation.manuscript.owner != request.user
        ):
            return JsonResponse(
                {"success": False, "error": "Permission denied"}, status=403
            )

        invitation.cancel()

        return JsonResponse({"success": True, "status": invitation.status})

    except CollaborationInvitation.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Invitation not found"}, status=404
        )
