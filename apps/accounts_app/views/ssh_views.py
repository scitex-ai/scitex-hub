"""SSH key management views."""
import subprocess
import tempfile
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts_app.models import UserProfile, WorkspaceSSHKey
from apps.accounts_app.utils.ssh_key_validator import SSHKeyValidator
from apps.project_app.models import RemoteCredential
from apps.project_app.services.gitea_sync_service import (
    remove_ssh_key_from_gitea,
    sync_ssh_key_to_gitea,
)
from apps.project_app.services.ssh_service import SSHKeyManager


def handle_git_ssh_key_actions(request, ssh_manager, profile):
    """Handle Git SSH key generation and deletion."""
    action = request.POST.get("action")

    if action == "generate":
        success, public_key, error = ssh_manager.get_or_create_user_key()
        if success:
            messages.success(request, "SSH key generated successfully!")

            # Sync SSH key to Gitea
            sync_success, sync_error = sync_ssh_key_to_gitea(request.user)
            if sync_success:
                messages.success(
                    request, "SSH key synced to Gitea - you can now use SSH clone!"
                )
            else:
                messages.warning(
                    request,
                    f"SSH key created but Gitea sync failed: {sync_error}. You may need to add the key manually to Gitea.",
                )
        else:
            messages.error(request, f"Failed to generate SSH key: {error}")

    elif action == "delete":
        success, error = ssh_manager.delete_user_key()
        if success:
            messages.success(request, "SSH key deleted successfully!")

            # Remove SSH key from Gitea
            remove_success, remove_error = remove_ssh_key_from_gitea(request.user)
            if remove_success:
                messages.success(request, "SSH key removed from Gitea")
            else:
                messages.warning(
                    request,
                    f"SSH key deleted locally but Gitea removal failed: {remove_error}",
                )
        else:
            messages.error(request, f"Failed to delete SSH key: {error}")


def handle_workspace_ssh_key_actions(request):
    """Handle workspace SSH key addition and deletion."""
    action = request.POST.get("action")

    if action == "add_workspace_key":
        title = request.POST.get("title", "").strip()
        public_key = request.POST.get("public_key", "").strip()
        sync_to_gitea = request.POST.get("sync_to_gitea") == "on"

        if not title or not public_key:
            messages.error(request, "Both title and public key are required")
            return

        # Validate SSH key
        result = SSHKeyValidator.validate_and_parse(public_key)

        if not result["valid"]:
            messages.error(request, f"Invalid SSH key: {result['error']}")
            return

        # Check for duplicate fingerprint
        if WorkspaceSSHKey.objects.filter(
            user=request.user, fingerprint=result["fingerprint"]
        ).exists():
            messages.error(
                request, "This SSH key is already registered to your account"
            )
            return

        # Create new workspace SSH key
        workspace_key = WorkspaceSSHKey.objects.create(
            user=request.user,
            title=title,
            public_key=result["formatted_key"],
            fingerprint=result["fingerprint"],
            key_type=result["key_type"],
        )
        messages.success(
            request,
            f'SSH key "{title}" added successfully! You can now use it to connect to your workspace.',
        )

        # Optionally sync to Gitea
        if sync_to_gitea:
            from apps.gitea_app.api_client import GiteaClient

            try:
                client = GiteaClient()
                # Check if key already exists in Gitea by fingerprint
                existing_key = client.find_ssh_key_by_fingerprint(
                    result["fingerprint"].replace("SHA256:", ""),
                    request.user.username,
                )

                if not existing_key:
                    client.add_ssh_key(
                        title=f"{title} (Workspace Key)",
                        key=result["formatted_key"],
                        username=request.user.username,
                    )
                    messages.success(
                        request,
                        f'SSH key also synced to Gitea! You can now use it for: git clone ssh://git@127.0.0.1:2222/...',
                    )
                else:
                    messages.info(
                        request, "SSH key already exists in Gitea - no sync needed"
                    )
            except Exception as e:
                messages.warning(
                    request,
                    f"Workspace key added but Gitea sync failed: {str(e)}. You can add it manually in Gitea.",
                )

    elif action == "delete_workspace_key":
        key_id = request.POST.get("key_id")
        try:
            key = WorkspaceSSHKey.objects.get(id=key_id, user=request.user)
            key_title = key.title
            key.delete()
            messages.success(request, f'SSH key "{key_title}" deleted successfully!')
        except WorkspaceSSHKey.DoesNotExist:
            messages.error(request, "SSH key not found")


@login_required
def ssh_keys(request):
    """SSH key management page."""
    ssh_manager = SSHKeyManager(request.user)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        # Handle Git SSH key actions
        if action in ["generate", "delete"]:
            handle_git_ssh_key_actions(request, ssh_manager, profile)
        # Handle Workspace SSH key actions
        elif action in ["add_workspace_key", "delete_workspace_key"]:
            handle_workspace_ssh_key_actions(request)
        # Handle Remote credential actions (delegated to remote_credentials module)
        elif action in ["add_remote_credential", "delete_remote_credential", "test_remote_credential"]:
            # These are handled in the remote_credentials view
            pass

        return redirect("accounts_app:ssh_keys")

    # GET request
    workspace_ssh_keys = WorkspaceSSHKey.objects.filter(user=request.user).order_by(
        "-created_at"
    )

    # Get remote credentials
    remote_credentials = RemoteCredential.objects.filter(user=request.user).order_by(
        '-last_used_at', '-created_at'
    )

    context = {
        # Git SSH keys
        "ssh_public_key": profile.ssh_public_key,
        "ssh_key_fingerprint": profile.ssh_key_fingerprint,
        "ssh_key_created_at": profile.ssh_key_created_at,
        "ssh_key_last_used_at": profile.ssh_key_last_used_at,
        "has_ssh_key": ssh_manager.has_ssh_key(),
        # Workspace SSH keys
        "workspace_ssh_keys": workspace_ssh_keys,
        # Remote credentials
        "remote_credentials": remote_credentials,
    }
    return render(request, "accounts_app/ssh_keys.html", context)


@login_required
@require_http_methods(["POST"])
def api_generate_ssh_key(request):
    """API endpoint to generate SSH key."""
    ssh_manager = SSHKeyManager(request.user)
    success, public_key, error = ssh_manager.get_or_create_user_key()

    if success:
        # Sync SSH key to Gitea
        sync_success, sync_error = sync_ssh_key_to_gitea(request.user)

        return JsonResponse(
            {
                "success": True,
                "public_key": public_key,
                "gitea_synced": sync_success,
                "gitea_error": sync_error,
            }
        )
    else:
        return JsonResponse({"success": False, "error": error}, status=400)
