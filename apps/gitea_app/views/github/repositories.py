"""
GitHub Repository Management Views
Create and link GitHub repositories to projects
"""

import requests
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from ...models import Project


@login_required
@require_http_methods(["POST"])
def github_create_repository(request):
    """Create a new GitHub repository"""
    project_id = request.POST.get("project_id")
    repo_name = request.POST.get("repo_name")
    is_private = request.POST.get("is_private", "false").lower() == "true"
    description = request.POST.get("description", "")

    if not project_id or not repo_name:
        return JsonResponse(
            {"error": "Project ID and repository name required"}, status=400
        )

    project = get_object_or_404(Project, id=project_id, owner=request.user)

    if not project.github_token:
        return JsonResponse({"error": "GitHub not connected"}, status=400)

    # Create repository via GitHub API
    repo_data = {
        "name": repo_name,
        "description": description or f"Research project: {project.name}",
        "private": is_private,
        "auto_init": True,
        "gitignore_template": "Python",  # Research-friendly template
    }

    response = requests.post(
        "https://api.github.com/user/repos",
        headers={
            "Authorization": f"token {project.github_token}",
            "Accept": "application/vnd.github.v3+json",
        },
        json=repo_data,
    )

    if response.status_code == 201:
        repo_info = response.json()

        # Update project with repository info
        project.github_repo_id = repo_info["id"]
        project.github_repo_name = repo_info["name"]
        project.source_code_url = repo_info["html_url"]
        project.current_branch = repo_info["default_branch"]
        project.last_sync_at = timezone.now()
        project.save()

        return JsonResponse(
            {
                "success": True,
                "repository": {
                    "id": repo_info["id"],
                    "name": repo_info["name"],
                    "url": repo_info["html_url"],
                    "clone_url": repo_info["clone_url"],
                },
            }
        )

    return JsonResponse({"error": "Failed to create repository"}, status=400)


@login_required
@require_http_methods(["POST"])
def github_link_repository(request):
    """Link existing GitHub repository to project"""
    project_id = request.POST.get("project_id")
    repo_url = request.POST.get("repo_url")

    if not project_id or not repo_url:
        return JsonResponse(
            {"error": "Project ID and repository URL required"}, status=400
        )

    project = get_object_or_404(Project, id=project_id, owner=request.user)

    if not project.github_token:
        return JsonResponse({"error": "GitHub not connected"}, status=400)

    # Parse repository URL to get owner/repo
    try:
        if "github.com/" in repo_url:
            parts = repo_url.split("github.com/")[-1].strip("/").split("/")
            if len(parts) >= 2:
                owner, repo_name = parts[0], parts[1]
            else:
                return JsonResponse({"error": "Invalid repository URL"}, status=400)
        else:
            return JsonResponse({"error": "Not a valid GitHub URL"}, status=400)
    except Exception:
        return JsonResponse({"error": "Could not parse repository URL"}, status=400)

    # Get repository info from GitHub API
    response = requests.get(
        f"https://api.github.com/repos/{owner}/{repo_name}",
        headers={
            "Authorization": f"token {project.github_token}",
            "Accept": "application/vnd.github.v3+json",
        },
    )

    if response.status_code == 200:
        repo_info = response.json()

        # Update project with repository info
        project.github_repo_id = repo_info["id"]
        project.github_repo_name = repo_info["name"]
        project.github_owner = repo_info["owner"]["login"]
        project.source_code_url = repo_info["html_url"]
        project.current_branch = repo_info["default_branch"]
        project.last_sync_at = timezone.now()
        project.save()

        return JsonResponse(
            {
                "success": True,
                "repository": {
                    "id": repo_info["id"],
                    "name": repo_info["name"],
                    "owner": repo_info["owner"]["login"],
                    "url": repo_info["html_url"],
                },
            }
        )

    return JsonResponse({"error": "Repository not found or access denied"}, status=404)


@login_required
@require_http_methods(["GET"])
def github_list_repositories(request):
    """List user's GitHub repositories"""
    # This would require a valid GitHub token stored in user session or profile
    # For now, return empty list
    return JsonResponse(
        {
            "repositories": [],
            "message": "Connect to GitHub first to see your repositories",
        }
    )
