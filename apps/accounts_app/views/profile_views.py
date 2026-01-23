"""Profile management views."""
import logging
import os
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts_app.models import UserProfile

logger = logging.getLogger(__name__)


def calculate_storage_usage(user):
    """Calculate storage usage for user's local projects."""
    from apps.project_app.models import Project

    total_storage_bytes = 0
    try:
        for project in Project.objects.filter(user=user, project_type='local'):
            project_path = Path(project.git_clone_path) if hasattr(project, 'git_clone_path') and project.git_clone_path else None
            if project_path and project_path.exists():
                for root, dirs, files in os.walk(project_path):
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            if os.path.exists(file_path):
                                total_storage_bytes += os.path.getsize(file_path)
                        except (OSError, FileNotFoundError):
                            pass
    except Exception as e:
        logger.warning(f"Error calculating storage usage: {e}")

    return total_storage_bytes


def human_readable_size(bytes_size):
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


def gather_resource_statistics(user):
    """Gather comprehensive resource allocation statistics."""
    from apps.code_app.models import ProjectService
    from apps.project_app.models import Project, RemoteCredential

    # Project statistics
    total_projects = Project.objects.filter(owner=user).count()
    local_projects = Project.objects.filter(owner=user, project_type='local').count()
    remote_projects = Project.objects.filter(owner=user, project_type='remote').count()

    # Remote credentials
    remote_credentials_count = RemoteCredential.objects.filter(user=user, is_active=True).count()

    # Active services (TensorBoard, Jupyter, etc.)
    active_services = ProjectService.objects.filter(
        user=user,
        status__in=['starting', 'running']
    ).count()

    # SSH keys count
    workspace_ssh_keys = user.ssh_public_keys.filter(key_type='workspace').count()
    git_ssh_keys = user.ssh_public_keys.filter(key_type='git').count()
    total_ssh_keys = workspace_ssh_keys + git_ssh_keys

    # Storage usage
    total_storage_bytes = calculate_storage_usage(user)
    storage_used = human_readable_size(total_storage_bytes)

    # Collaborations
    total_collaborations = Project.objects.filter(collaborators=user).count()

    return {
        "total_projects": total_projects,
        "local_projects": local_projects,
        "remote_projects": remote_projects,
        "remote_credentials": remote_credentials_count,
        "active_services": active_services,
        "total_ssh_keys": total_ssh_keys,
        "workspace_ssh_keys": workspace_ssh_keys,
        "git_ssh_keys": git_ssh_keys,
        "storage_used": storage_used,
        "storage_bytes": total_storage_bytes,
        "total_collaborations": total_collaborations,
    }


@login_required
def profile_view(request):
    """User profile view."""
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    resources = gather_resource_statistics(request.user)

    context = {
        "profile": profile,
        "resources": resources,
    }

    return render(request, "accounts_app/profile.html", context)


@login_required
def profile_edit(request):
    """Edit user profile (GitHub-style settings page)."""
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # Update user basic info
        request.user.first_name = request.POST.get("first_name", "").strip()
        request.user.last_name = request.POST.get("last_name", "").strip()
        request.user.email = request.POST.get("email", "").strip()
        request.user.save()

        # Update profile info
        profile.bio = request.POST.get("bio", "").strip()
        profile.location = request.POST.get("location", "").strip()
        profile.timezone = request.POST.get("timezone", "").strip() or "UTC"
        profile.institution = request.POST.get("institution", "").strip()
        profile.website = request.POST.get("website", "").strip()
        profile.orcid = request.POST.get("orcid", "").strip()
        profile.google_scholar = request.POST.get("google_scholar", "").strip()
        profile.twitter = request.POST.get("twitter", "").strip()

        # Handle avatar upload
        if "avatar" in request.FILES:
            profile.avatar = request.FILES["avatar"]

        profile.save()

        messages.success(request, "Profile updated successfully!")
        return redirect("accounts_app:profile_edit")

    context = {
        "profile": profile,
        "user": request.user,
    }

    return render(request, "accounts_app/profile_edit.html", context)


@login_required
def appearance_settings(request):
    """Appearance settings page (GitHub-style /settings/appearance)."""
    context = {
        "user": request.user,
    }
    return render(request, "accounts_app/appearance_settings.html", context)
