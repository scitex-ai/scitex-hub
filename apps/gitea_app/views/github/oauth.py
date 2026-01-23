"""
GitHub OAuth Authentication Views
Handles OAuth flow and token exchange for GitHub integration
"""

import requests
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from ...models import Project


# GitHub OAuth Configuration
GITHUB_CLIENT_ID = getattr(settings, "GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = getattr(settings, "GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI = getattr(settings, "GITHUB_REDIRECT_URI", "")


@login_required
@require_http_methods(["POST"])
def github_oauth_initiate(request):
    """Initiate GitHub OAuth flow"""
    project_id = request.POST.get("project_id")
    if not project_id:
        return JsonResponse({"error": "Project ID required"}, status=400)

    project = get_object_or_404(Project, id=project_id, owner=request.user)

    # Store project ID in session for callback
    request.session["github_project_id"] = project_id

    # GitHub OAuth URL
    oauth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_REDIRECT_URI}"
        f"&scope=repo,user:email"
        f"&state={project_id}"
    )

    return JsonResponse({"success": True, "oauth_url": oauth_url})


@login_required
@require_http_methods(["GET"])
def github_oauth_callback(request):
    """Handle GitHub OAuth callback"""
    code = request.GET.get("code")
    state = request.GET.get("state")  # project_id

    if not code or not state:
        return JsonResponse({"error": "Invalid OAuth callback"}, status=400)

    project = get_object_or_404(Project, id=state, owner=request.user)

    # Exchange code for access token
    token_response = requests.post(
        "https://github.com/login/oauth/access_token",
        {
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
        },
        headers={"Accept": "application/json"},
    )

    if token_response.status_code != 200:
        return JsonResponse({"error": "Failed to get access token"}, status=400)

    token_data = token_response.json()
    access_token = token_data.get("access_token")

    if not access_token:
        return JsonResponse({"error": "No access token received"}, status=400)

    # Get user info from GitHub
    user_response = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"token {access_token}"},
    )

    if user_response.status_code == 200:
        user_data = user_response.json()

        # Update project with GitHub token
        project.github_token = access_token
        project.github_owner = user_data.get("login")
        project.github_integration_enabled = True
        project.last_sync_at = timezone.now()
        project.save()

        return JsonResponse(
            {
                "success": True,
                "message": "GitHub connected successfully",
                "github_username": user_data.get("login"),
            }
        )

    return JsonResponse({"error": "Failed to get user info"}, status=400)
