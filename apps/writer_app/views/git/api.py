"""API endpoints for Git operations on writer workspace."""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ...decorators import writer_auth_required, writer_project_access_required
from ...services import WriterService
import json
import logging

logger = logging.getLogger(__name__)


@writer_auth_required
@writer_project_access_required
@require_http_methods(["GET"])
def git_history_api(request, project_id):
    """Get Git commit history for writer directory.

    Query params:
        - max_count: Number of commits to return (default: 50)
        - branch: Branch name (default: HEAD/current branch)

    Returns:
        {
            "success": true,
            "commits": [
                {
                    "sha": "full_sha",
                    "sha_short": "short_sha",
                    "message": "commit message",
                    "author_name": "author",
                    "author_email": "email",
                    "date": "2025-01-13T12:00:00",
                    "date_relative": "2 hours ago",
                    "parent_shas": ["parent_sha"],
                    "stats": {
                        "files_changed": 3,
                        "insertions": 15,
                        "deletions": 5
                    }
                },
                ...
            ]
        }
    """
    try:
        max_count = int(request.GET.get("max_count", 50))
        branch = request.GET.get("branch", "HEAD")

        writer_service = WriterService(project_id, request.effective_user.id)
        commits = writer_service.git_service.get_commit_history(
            max_count=max_count, branch=branch
        )

        # Convert datetime objects to ISO format strings
        for commit in commits:
            commit["date"] = commit["date"].isoformat()

        return JsonResponse({"success": True, "commits": commits})

    except Exception as e:
        logger.error(f"Error getting git history: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@writer_auth_required
@writer_project_access_required
@require_http_methods(["GET"])
def git_diff_api(request, project_id):
    """Get Git diff for specific commit or working directory.

    Query params:
        - commit_sha: Commit SHA to show diff for (optional, default: working directory)
        - compare_to: Commit SHA to compare against (optional, default: previous commit or HEAD)

    Returns:
        {
            "success": true,
            "diff": {
                "files": [
                    {
                        "path": "file/path.tex",
                        "change_type": "modified|added|deleted|renamed",
                        "diff": "diff content",
                        "insertions": 10,
                        "deletions": 5
                    },
                    ...
                ],
                "stats": {
                    "files": 3,
                    "insertions": 15,
                    "deletions": 8
                }
            }
        }
    """
    try:
        commit_sha = request.GET.get("commit_sha")
        compare_to = request.GET.get("compare_to")

        writer_service = WriterService(project_id, request.effective_user.id)
        diff_data = writer_service.git_service.get_diff(
            commit_sha=commit_sha, compare_to=compare_to
        )

        return JsonResponse({"success": True, "diff": diff_data})

    except Exception as e:
        logger.error(f"Error getting git diff: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@writer_auth_required
@writer_project_access_required
@require_http_methods(["GET"])
def git_status_api(request, project_id):
    """Get current Git repository status.

    Returns:
        {
            "success": true,
            "status": {
                "branch": "main",
                "clean": true,
                "files": {
                    "modified": ["file1.tex"],
                    "staged": ["file2.tex"],
                    "untracked": ["file3.tex"]
                }
            }
        }
    """
    try:
        writer_service = WriterService(project_id, request.effective_user.id)
        status = writer_service.git_service.get_status()

        return JsonResponse({"success": True, "status": status})

    except Exception as e:
        logger.error(f"Error getting git status: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@writer_auth_required
@writer_project_access_required
@require_http_methods(["GET"])
def git_branches_api(request, project_id):
    """Get list of Git branches.

    Returns:
        {
            "success": true,
            "branches": [
                {
                    "name": "main",
                    "is_current": true,
                    "commit_sha": "full_sha",
                    "commit_sha_short": "short_sha",
                    "commit_message": "latest commit",
                    "last_commit_date": "2025-01-13T12:00:00"
                },
                ...
            ]
        }
    """
    try:
        writer_service = WriterService(project_id, request.effective_user.id)
        branches = writer_service.git_service.get_branches()

        # Convert datetime objects to ISO format strings
        for branch in branches:
            branch["last_commit_date"] = branch["last_commit_date"].isoformat()

        return JsonResponse({"success": True, "branches": branches})

    except Exception as e:
        logger.error(f"Error getting git branches: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@writer_auth_required
@writer_project_access_required
@require_http_methods(["POST"])
def git_create_branch_api(request, project_id):
    """Create a new Git branch.

    POST body:
        {
            "branch_name": "feature/new-section",
            "from_commit": "commit_sha"  # optional
        }

    Returns:
        {
            "success": true,
            "message": "Branch created successfully"
        }
    """
    try:
        data = json.loads(request.body)
        branch_name = data.get("branch_name")
        from_commit = data.get("from_commit")

        if not branch_name:
            return JsonResponse(
                {"success": False, "error": "branch_name required"}, status=400
            )

        writer_service = WriterService(project_id, request.effective_user.id)
        success = writer_service.git_service.create_branch(
            branch_name=branch_name, from_commit=from_commit
        )

        if success:
            return JsonResponse(
                {"success": True, "message": f"Branch '{branch_name}' created successfully"}
            )
        else:
            return JsonResponse(
                {"success": False, "error": "Failed to create branch"}, status=500
            )

    except Exception as e:
        logger.error(f"Error creating git branch: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@writer_auth_required
@writer_project_access_required
@require_http_methods(["POST"])
def git_switch_branch_api(request, project_id):
    """Switch to a different Git branch.

    POST body:
        {
            "branch_name": "feature/new-section"
        }

    Returns:
        {
            "success": true,
            "message": "Switched to branch successfully"
        }
    """
    try:
        data = json.loads(request.body)
        branch_name = data.get("branch_name")

        if not branch_name:
            return JsonResponse(
                {"success": False, "error": "branch_name required"}, status=400
            )

        writer_service = WriterService(project_id, request.effective_user.id)
        success = writer_service.git_service.switch_branch(branch_name=branch_name)

        if success:
            return JsonResponse(
                {
                    "success": True,
                    "message": f"Switched to branch '{branch_name}' successfully",
                }
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Failed to switch branch (uncommitted changes?)",
                },
                status=400,
            )

    except Exception as e:
        logger.error(f"Error switching git branch: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@writer_auth_required
@writer_project_access_required
@require_http_methods(["POST"])
def git_commit_api(request, project_id):
    """Create a Git commit.

    POST body:
        {
            "message": "Update introduction section",
            "author_name": "User Name",  # optional
            "author_email": "user@email.com"  # optional
        }

    Returns:
        {
            "success": true,
            "commit_sha": "full_commit_sha",
            "commit_sha_short": "short_sha"
        }
    """
    try:
        data = json.loads(request.body)
        message = data.get("message")
        author_name = data.get("author_name")
        author_email = data.get("author_email")

        if not message:
            return JsonResponse(
                {"success": False, "error": "commit message required"}, status=400
            )

        writer_service = WriterService(project_id, request.effective_user.id)
        commit_sha = writer_service.git_service.commit(
            message=message,
            author_name=author_name,
            author_email=author_email,
            auto_stage=True,
        )

        if commit_sha:
            return JsonResponse(
                {
                    "success": True,
                    "commit_sha": commit_sha,
                    "commit_sha_short": commit_sha[:8],
                    "message": "Commit created successfully",
                }
            )
        else:
            return JsonResponse(
                {"success": True, "message": "No changes to commit"}, status=200
            )

    except Exception as e:
        logger.error(f"Error creating git commit: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)
