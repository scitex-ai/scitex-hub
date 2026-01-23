"""Remote SSH credentials management views."""
import subprocess
import tempfile
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.project_app.models import RemoteCredential


def generate_ssh_key_fingerprint(ssh_public_key):
    """Generate SSH key fingerprint from public key."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pub') as f:
            f.write(ssh_public_key)
            temp_pub_path = f.name

        result = subprocess.run(
            ['ssh-keygen', '-lf', temp_pub_path],
            capture_output=True,
            text=True,
            check=True
        )
        fingerprint = result.stdout.split()[1] if result.stdout else "Unknown"
        Path(temp_pub_path).unlink()
        return fingerprint

    except Exception as e:
        raise ValueError(f"Invalid SSH public key: {str(e)}")


def test_remote_credential_connection(credential):
    """Test SSH connection to remote credential."""
    ssh_key_path = credential.private_key_path

    cmd = [
        "ssh",
        "-p", str(credential.ssh_port),
        "-i", ssh_key_path,
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=10",
        f"{credential.ssh_username}@{credential.ssh_host}",
        "echo 'OK'"
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=15
    )

    return result.returncode == 0, result.stderr if result.returncode != 0 else None


def handle_add_remote_credential(request):
    """Handle adding a new remote credential."""
    name = request.POST.get("name", "").strip()
    ssh_host = request.POST.get("ssh_host", "").strip()
    ssh_port = request.POST.get("ssh_port", "22").strip()
    ssh_username = request.POST.get("ssh_username", "").strip()
    ssh_public_key = request.POST.get("ssh_public_key", "").strip()

    # Validate inputs
    if not all([name, ssh_host, ssh_username, ssh_public_key]):
        messages.error(request, "All fields are required")
        return False

    try:
        ssh_port = int(ssh_port)
    except ValueError:
        messages.error(request, "Invalid SSH port number")
        return False

    # Generate SSH key fingerprint
    try:
        fingerprint = generate_ssh_key_fingerprint(ssh_public_key)
    except ValueError as e:
        messages.error(request, str(e))
        return False

    # Generate private key path
    private_key_path = f"/home/{request.user.username}/.ssh/scitex_remote_{name.lower().replace(' ', '_')}"

    # Create credential
    try:
        RemoteCredential.objects.create(
            user=request.user,
            name=name,
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ssh_username=ssh_username,
            ssh_public_key=ssh_public_key,
            ssh_key_fingerprint=fingerprint,
            private_key_path=private_key_path,
            is_active=True
        )

        messages.success(
            request,
            f"Remote credential '{name}' added successfully! "
            f"Please ensure your private key is at: {private_key_path}"
        )
        return True

    except Exception as e:
        messages.error(request, f"Failed to add credential: {str(e)}")
        return False


def handle_delete_remote_credential(request):
    """Handle deleting a remote credential."""
    credential_id = request.POST.get("credential_id")

    try:
        credential = RemoteCredential.objects.get(id=credential_id, user=request.user)
        credential_name = credential.name
        credential.delete()
        messages.success(request, f"Remote credential '{credential_name}' deleted")
        return True

    except RemoteCredential.DoesNotExist:
        messages.error(request, "Credential not found")
        return False


def handle_test_remote_credential(request):
    """Handle testing remote credential connection."""
    credential_id = request.POST.get("credential_id")

    try:
        credential = RemoteCredential.objects.get(id=credential_id, user=request.user)

        try:
            success, error = test_remote_credential_connection(credential)

            if success:
                messages.success(request, f"Connection successful to {credential.name}")
            else:
                messages.error(request, f"Connection failed to {credential.name}: {error}")

        except subprocess.TimeoutExpired:
            messages.error(request, "Connection timeout")
        except Exception as e:
            messages.error(request, f"Connection test failed: {str(e)}")

        return True

    except RemoteCredential.DoesNotExist:
        messages.error(request, "Credential not found")
        return False


@login_required
def remote_credentials(request):
    """Remote credentials management page."""
    credentials = RemoteCredential.objects.filter(user=request.user).order_by(
        '-last_used_at', '-created_at'
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            handle_add_remote_credential(request)
        elif action == "delete":
            handle_delete_remote_credential(request)
        elif action == "test":
            handle_test_remote_credential(request)

        return redirect("accounts_app:remote_credentials")

    context = {
        "credentials": credentials,
    }

    return render(request, "accounts_app/remote_credentials.html", context)
