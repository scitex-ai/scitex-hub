"""
Settings Views
Handles project settings and configuration.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from apps.project_app.models import Project, ProjectMembership, ProjectInvitation
import logging

logger = logging.getLogger(__name__)


@login_required
def project_settings(request, username, slug):
    """GitHub-style repository settings page"""
    logger.info(
        f"[Settings VIEW] ===== ENTERED ===== Method: {request.method}, User: {request.user.username if request.user.is_authenticated else 'Visitor'}, Path: {request.path}"
    )

    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Only project owner can access settings
    if project.owner != request.user:
        messages.error(request, "You don't have permission to access settings.")
        return redirect("user_projects:detail", username=username, slug=slug)

    if request.method == "POST":
        action = request.POST.get("action")
        logger.info(f"[Settings POST] ===== POST RECEIVED =====")
        logger.info(f"[Settings POST] Action: '{action}'")
        logger.info(f"[Settings POST] User: {request.user.username}")
        logger.info(f"[Settings POST] Project: {project.slug}")
        logger.info(f"[Settings POST] All POST keys: {list(request.POST.keys())}")
        logger.info(
            f"[Settings POST] collaborator_username: {request.POST.get('collaborator_username')}"
        )
        logger.info(
            f"[Settings POST] collaborator_role: {request.POST.get('collaborator_role')}"
        )

        if action == "update_general":
            # Update basic project info
            project.name = request.POST.get("name", "").strip()
            project.description = request.POST.get("description", "").strip()
            project.save()
            messages.success(request, "General settings updated successfully")

        elif action == "update_visibility":
            # Update visibility
            new_visibility = request.POST.get("visibility")
            if new_visibility in ["public", "private"]:
                project.visibility = new_visibility
                project.save()
                messages.success(
                    request,
                    f"Repository visibility updated to {new_visibility}",
                )

        elif action == "add_collaborator":
            # Send invitation to collaborator
            from apps.project_app.services.email_service import EmailService

            collaborator_username = request.POST.get(
                "collaborator_username", ""
            ).strip()
            collaborator_role = request.POST.get("collaborator_role", "collaborator")

            # Map role to permission_level
            role_permission_map = {
                "viewer": "read",
                "collaborator": "write",
                "admin": "admin",
            }
            permission_level = role_permission_map.get(collaborator_role, "write")

            if collaborator_username:
                try:
                    collaborator = User.objects.get(username=collaborator_username)

                    # Check if already a collaborator
                    if ProjectMembership.objects.filter(
                        project=project, user=collaborator
                    ).exists():
                        messages.warning(
                            request,
                            f"{collaborator_username} is already a collaborator",
                        )
                    elif collaborator == project.owner:
                        messages.warning(
                            request,
                            "Repository owner is already a collaborator",
                        )
                    elif ProjectInvitation.objects.filter(
                        project=project, invited_user=collaborator, status="pending"
                    ).exists():
                        messages.warning(
                            request,
                            f"Invitation already sent to {collaborator_username}",
                        )
                    else:
                        # Create invitation
                        try:
                            invitation = ProjectInvitation.objects.create(
                                project=project,
                                invited_user=collaborator,
                                invited_by=request.user,
                                role=collaborator_role,
                                permission_level=permission_level,
                            )
                            logger.info(
                                f"Created invitation: {invitation.id} for {collaborator_username}"
                            )

                            # Send email notification if user has email
                            if collaborator.email:
                                try:
                                    email_service = EmailService()
                                    accept_url = request.build_absolute_uri(
                                        f"/invitations/{invitation.token}/accept/"
                                    )
                                    decline_url = request.build_absolute_uri(
                                        f"/invitations/{invitation.token}/decline/"
                                    )

                                    email_service.send_email(
                                        to_email=collaborator.email,
                                        subject=f"{request.user.username} invited you to collaborate on {project.name}",
                                        html_content=f'''
                                        <h2>You've been invited to collaborate!</h2>
                                        <p><strong>{request.user.username}</strong> has invited you to collaborate on the project <strong>{project.name}</strong>.</p>
                                        <p><strong>Role:</strong> {collaborator_role.title()} ({permission_level})</p>
                                        <p><a href="{accept_url}" style="display: inline-block; padding: 12px 24px; background: #10b981; color: white; text-decoration: none; border-radius: 6px; font-weight: 600;">Accept Invitation</a></p>
                                        <p><a href="{decline_url}" style="color: #6b7280;">Decline</a></p>
                                        <p style="color: #6b7280; font-size: 12px; margin-top: 24px;">This invitation expires in 7 days.</p>
                                        ''',
                                        plain_content=f"{request.user.username} invited you to collaborate on {project.name}. Visit {accept_url} to accept.",
                                    )
                                    logger.info(
                                        f"Sent invitation email to {collaborator.email}"
                                    )
                                    messages.success(
                                        request,
                                        f"✓ Invitation sent to {collaborator_username}! They'll receive an email at {collaborator.email}",
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"Failed to send invitation email to {collaborator.email}: {e}",
                                        exc_info=True,
                                    )
                                    messages.warning(
                                        request,
                                        f"Invitation created for {collaborator_username}, but email failed. They can check /invitations/",
                                    )
                            else:
                                # No email - just notify
                                logger.warning(
                                    f"User {collaborator_username} has no email address"
                                )
                                messages.success(
                                    request,
                                    f"✓ Invitation created for {collaborator_username} (they have no email set - they can check /invitations/)",
                                )
                        except Exception as e:
                            logger.error(
                                f"Failed to create invitation: {e}", exc_info=True
                            )
                            messages.error(request, f"Failed to create invitation: {e}")

                except User.DoesNotExist:
                    messages.error(request, f'User "{collaborator_username}" not found')
            else:
                messages.error(request, "Please enter a username")

        elif action == "delete_repository":
            # Delete repository
            project_name = project.name
            project.delete()
            messages.success(request, f'Repository "{project_name}" has been deleted')
            return redirect(f"/{request.user.username}/")

        return redirect("user_projects:settings", username=username, slug=slug)

    context = {
        "project": project,
    }
    return render(request, "project_app/projects/settings.html", context)


# EOF
