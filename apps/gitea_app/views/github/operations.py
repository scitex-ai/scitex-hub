"""
GitHub Git Operations Views
Commit and push changes to GitHub
"""

import subprocess
import os
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from ...models import Project, GitFileStatus


@login_required
@require_http_methods(["POST"])
def github_commit_files(request, project_id):
    """Commit staged files to Git"""
    project = get_object_or_404(Project, id=project_id, owner=request.user)

    if not project.is_github_connected():
        return JsonResponse({"error": "GitHub not connected"}, status=400)

    commit_message = request.POST.get("commit_message", "").strip()
    if not commit_message:
        return JsonResponse({"error": "Commit message required"}, status=400)

    project_path = project.get_directory_path()
    if not project_path or not project_path.exists():
        return JsonResponse({"error": "Project directory not found"}, status=400)

    try:
        original_cwd = os.getcwd()
        os.chdir(project_path)

        # Configure git user if not set
        subprocess.run(
            ["git", "config", "user.email", request.user.email],
            capture_output=True,
            timeout=10,
        )
        subprocess.run(
            [
                "git",
                "config",
                "user.name",
                request.user.get_full_name() or request.user.username,
            ],
            capture_output=True,
            timeout=10,
        )

        # Add all modified files
        add_result = subprocess.run(
            ["git", "add", "."], capture_output=True, text=True, timeout=30
        )

        if add_result.returncode != 0:
            return JsonResponse({"error": "Failed to stage files"}, status=400)

        # Commit changes
        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if commit_result.returncode != 0:
            if "nothing to commit" in commit_result.stdout:
                return JsonResponse({"error": "No changes to commit"}, status=400)
            else:
                return JsonResponse({"error": "Commit failed"}, status=400)

        # Update file statuses
        GitFileStatus.objects.filter(
            project=project, git_status__in=["modified", "added", "untracked"]
        ).update(git_status="committed")

        return JsonResponse(
            {
                "success": True,
                "message": "Changes committed successfully",
                "commit_message": commit_message,
            }
        )

    except subprocess.TimeoutExpired:
        return JsonResponse({"error": "Git command timed out"}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"Commit failed: {str(e)}"}, status=500)
    finally:
        os.chdir(original_cwd)


@login_required
@require_http_methods(["POST"])
def github_push_changes(request, project_id):
    """Push committed changes to GitHub"""
    project = get_object_or_404(Project, id=project_id, owner=request.user)

    if not project.is_github_connected():
        return JsonResponse({"error": "GitHub not connected"}, status=400)

    project_path = project.get_directory_path()
    if not project_path or not project_path.exists():
        return JsonResponse({"error": "Project directory not found"}, status=400)

    try:
        original_cwd = os.getcwd()
        os.chdir(project_path)

        # Push to current branch
        push_result = subprocess.run(
            ["git", "push", "origin", project.current_branch],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if push_result.returncode != 0:
            return JsonResponse(
                {"error": f"Push failed: {push_result.stderr}"}, status=400
            )

        # Update sync time
        project.last_sync_at = timezone.now()
        project.save()

        return JsonResponse(
            {
                "success": True,
                "message": f"Changes pushed to {project.current_branch} branch",
            }
        )

    except subprocess.TimeoutExpired:
        return JsonResponse({"error": "Push command timed out"}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"Push failed: {str(e)}"}, status=500)
    finally:
        os.chdir(original_cwd)
