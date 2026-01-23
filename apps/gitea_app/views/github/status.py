"""
GitHub Status and Sync Views
Monitor and sync Git status for project files
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
@require_http_methods(["GET"])
def github_get_status(request, project_id):
    """Get GitHub integration status for project"""
    project = get_object_or_404(Project, id=project_id, owner=request.user)

    status_info = {
        "connected": project.is_github_connected(),
        "status": project.get_github_status(),
        "repository_url": project.get_github_repo_url(),
        "current_branch": project.current_branch,
        "last_sync": project.last_sync_at.isoformat() if project.last_sync_at else None,
    }

    if project.is_github_connected():
        # Get file status summary
        file_statuses = GitFileStatus.objects.filter(project=project)
        status_info["file_stats"] = {
            "total_files": file_statuses.count(),
            "modified": file_statuses.filter(git_status="modified").count(),
            "untracked": file_statuses.filter(git_status="untracked").count(),
            "staged": file_statuses.filter(git_status="staged").count(),
        }

    return JsonResponse(status_info)


@login_required
@require_http_methods(["POST"])
def github_sync_status(request, project_id):
    """Sync Git status for project files"""
    project = get_object_or_404(Project, id=project_id, owner=request.user)

    if not project.is_github_connected():
        return JsonResponse({"error": "GitHub not connected"}, status=400)

    project_path = project.get_directory_path()
    if not project_path or not project_path.exists():
        return JsonResponse({"error": "Project directory not found"}, status=400)

    try:
        # Change to project directory
        original_cwd = os.getcwd()
        os.chdir(project_path)

        # Run git status to get file statuses
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            return JsonResponse({"error": "Git status command failed"}, status=400)

        # Clear existing file statuses
        GitFileStatus.objects.filter(project=project).delete()

        # Parse git status output
        updated_files = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue

            status_code = line[:2]
            file_path = line[3:].strip()

            # Map git status codes to our model
            if status_code.strip() == "??":
                git_status = "untracked"
            elif status_code.strip() == "M":
                git_status = "modified"
            elif status_code.strip() == "A":
                git_status = "added"
            elif status_code.strip() == "D":
                git_status = "deleted"
            elif status_code.strip() == "R":
                git_status = "renamed"
            elif status_code.strip() == "C":
                git_status = "copied"
            else:
                git_status = "modified"

            # Create GitFileStatus record
            file_status = GitFileStatus.objects.create(
                project=project, file_path=file_path, git_status=git_status
            )

            updated_files.append(
                {
                    "path": file_path,
                    "status": git_status,
                    "icon": file_status.get_status_icon(),
                    "color": file_status.get_status_color(),
                }
            )

        # Update project sync time
        project.last_sync_at = timezone.now()
        project.save()

        return JsonResponse(
            {
                "success": True,
                "files_updated": len(updated_files),
                "files": updated_files,
            }
        )

    except subprocess.TimeoutExpired:
        return JsonResponse({"error": "Git command timed out"}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"Sync failed: {str(e)}"}, status=500)
    finally:
        os.chdir(original_cwd)
