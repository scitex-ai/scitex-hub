"""Remote SSH credentials management views."""

import subprocess
import tempfile
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.infra.project_app.models import RemoteCredential
from apps.infra.project_app.ssh_safety import (
    minimal_ssh_env,
    ssh_copy_id_argv,
    ssh_probe_argv,
    validate_ssh_host,
    validate_ssh_username,
)


def _get_user_ssh_dir(username):
    """Get the .ssh directory inside user's workspace."""
    from django.conf import settings

    user_data_root = Path(getattr(settings, "USER_DATA_ROOT", "/app/data/users"))
    return user_data_root / username / ".ssh"


def _sanitize_key_name(name):
    """Sanitize credential name for use as filename."""
    return name.lower().replace(" ", "_").replace("/", "_")


def _save_private_key(username, key_name, key_content):
    """Save private key to user's workspace .ssh directory.

    Returns the absolute path inside the container.
    """
    ssh_dir = _get_user_ssh_dir(username)
    ssh_dir.mkdir(parents=True, exist_ok=True)

    key_path = ssh_dir / f"id_{_sanitize_key_name(key_name)}"

    key_path.write_text(key_content)
    key_path.chmod(0o600)

    return str(key_path)


def _generate_key_pair(username, key_name):
    """Generate ed25519 SSH key pair in user's workspace.

    Returns (private_key_path, public_key_content, fingerprint).
    """
    ssh_dir = _get_user_ssh_dir(username)
    ssh_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_key_name(key_name)
    key_path = ssh_dir / f"id_{safe_name}"
    pub_path = ssh_dir / f"id_{safe_name}.pub"

    # Remove existing key if present
    if key_path.exists():
        key_path.unlink()
    if pub_path.exists():
        pub_path.unlink()

    # Generate ed25519 key pair
    result = subprocess.run(
        [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-f",
            str(key_path),
            "-N",
            "",  # no passphrase
            "-C",
            f"scitex-{username}-{safe_name}",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ssh-keygen failed: {result.stderr}")

    # Read public key and fingerprint
    public_key = pub_path.read_text().strip()

    fingerprint_result = subprocess.run(
        ["ssh-keygen", "-lf", str(pub_path)],
        capture_output=True,
        text=True,
    )
    fingerprint = (
        fingerprint_result.stdout.split()[1]
        if fingerprint_result.returncode == 0
        else "Unknown"
    )

    # Ensure private key permissions
    key_path.chmod(0o600)

    return str(key_path), public_key, fingerprint


def generate_ssh_key_fingerprint(ssh_public_key):
    """Generate SSH key fingerprint from public key."""
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pub") as f:
            f.write(ssh_public_key)
            temp_pub_path = f.name

        result = subprocess.run(
            ["ssh-keygen", "-lf", temp_pub_path],
            capture_output=True,
            text=True,
            check=True,
        )
        fingerprint = result.stdout.split()[1] if result.stdout else "Unknown"
        Path(temp_pub_path).unlink()
        return fingerprint

    except Exception as e:
        raise ValueError(f"Invalid SSH public key: {str(e)}") from e


def test_remote_credential_connection(credential, runner=subprocess.run):
    """Test SSH connection to remote credential.

    ``runner`` is an injectable subprocess.run seam (kept for the security
    regression test, which captures the argv/env without launching ssh).
    The argv carries a ``--`` end-of-options terminator before the
    destination and runs under a minimal, secret-free environment.
    """
    ssh_key_path = credential.private_key_path

    if not Path(ssh_key_path).exists():
        return False, f"Private key not found: {ssh_key_path}"

    cmd = ssh_probe_argv(
        ssh_port=credential.ssh_port,
        ssh_key=ssh_key_path,
        ssh_user=credential.ssh_username,
        ssh_host=credential.ssh_host,
        remote_command="echo OK",
    )

    result = runner(
        cmd,
        capture_output=True,
        text=True,
        timeout=15,
        env=minimal_ssh_env(),
    )

    return result.returncode == 0, result.stderr if result.returncode != 0 else None


def handle_add_remote_credential(request):
    """Handle adding a new remote credential.

    Supports two modes:
    - "generate": Generate new ed25519 key pair (recommended)
    - "upload": Paste or upload existing private key
    """
    name = request.POST.get("name", "").strip()
    ssh_host = request.POST.get("ssh_host", "").strip()
    ssh_port = request.POST.get("ssh_port", "22").strip()
    ssh_username = request.POST.get("ssh_username", "").strip()
    key_mode = request.POST.get("key_mode", "generate").strip()

    # Validate common inputs
    if not all([name, ssh_host, ssh_username]):
        messages.error(request, "Name, host, and username are required")
        return False

    try:
        ssh_port = int(ssh_port)
    except ValueError:
        messages.error(request, "Invalid SSH port number")
        return False

    # SECURITY: reject argument-injection-prone host/username BEFORE any
    # key generation or ORM write (SSH arg-injection → host RCE). Fail loud.
    from django.core.exceptions import ValidationError

    try:
        validate_ssh_username(ssh_username)
        validate_ssh_host(ssh_host)
    except ValidationError as e:
        messages.error(request, "; ".join(e.messages))
        return False

    # Handle key based on mode
    if key_mode == "generate":
        try:
            private_key_path, public_key, fingerprint = _generate_key_pair(
                request.user.username, name
            )
        except Exception as e:
            messages.error(request, f"Failed to generate key pair: {e}")
            return False
    else:
        # Upload mode: paste or file
        private_key_content = request.POST.get("private_key_content", "").strip()
        if not private_key_content and "private_key_file" in request.FILES:
            private_key_content = (
                request.FILES["private_key_file"].read().decode("utf-8")
            )

        if not private_key_content:
            messages.error(request, "Private key content is required")
            return False

        try:
            private_key_path = _save_private_key(
                request.user.username, name, private_key_content
            )
        except Exception as e:
            messages.error(request, f"Failed to save private key: {e}")
            return False

        public_key = request.POST.get("ssh_public_key", "").strip()
        fingerprint = ""
        if public_key:
            try:
                fingerprint = generate_ssh_key_fingerprint(public_key)
            except ValueError as e:
                messages.error(request, str(e))
                return False

    # Create credential
    try:
        credential = RemoteCredential.objects.create(
            user=request.user,
            name=name,
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ssh_username=ssh_username,
            ssh_public_key=public_key,
            ssh_key_fingerprint=fingerprint,
            private_key_path=private_key_path,
            is_active=True,
        )

        if key_mode == "generate":
            # Store credential ID so template can show public key
            request.session["new_credential_id"] = credential.id
            messages.success(
                request,
                f"Key pair generated for '{name}'. "
                "Copy the public key below to your remote system's "
                "~/.ssh/authorized_keys.",
            )
        else:
            messages.success(
                request,
                f"Remote credential '{name}' added. Key saved to: {private_key_path}",
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

        # Remove private key file
        key_path = Path(credential.private_key_path)
        if key_path.exists():
            key_path.unlink()

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
                messages.error(
                    request, f"Connection failed to {credential.name}: {error}"
                )

        except subprocess.TimeoutExpired:
            messages.error(request, "Connection timeout")
        except Exception as e:
            messages.error(request, f"Connection test failed: {str(e)}")

        return True

    except RemoteCredential.DoesNotExist:
        messages.error(request, "Credential not found")
        return False


def run_ssh_copy_id(credential, ssh_password, pub_key_path, runner=subprocess.run):
    """Run ``sshpass ... ssh-copy-id ...`` with a hardened argv/env.

    Pure helper (no request/DB) so the security regression test can capture
    the argv and env via the injectable ``runner`` seam without launching
    a subprocess. The argv carries a ``--`` end-of-options terminator before
    the destination, and runs under a minimal, secret-free environment.
    """
    cmd = ssh_copy_id_argv(
        ssh_password=ssh_password,
        pub_key_path=pub_key_path,
        ssh_port=credential.ssh_port,
        ssh_user=credential.ssh_username,
        ssh_host=credential.ssh_host,
    )
    return runner(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
        env=minimal_ssh_env(),
    )


def handle_ssh_copy_id(request):
    """Install public key on remote system via ssh-copy-id."""
    credential_id = request.POST.get("credential_id")
    ssh_password = request.POST.get("ssh_password", "")

    if not ssh_password:
        messages.error(request, "Password is required for ssh-copy-id")
        return False

    try:
        credential = RemoteCredential.objects.get(id=credential_id, user=request.user)
        pub_key_path = credential.private_key_path + ".pub"

        if not Path(pub_key_path).exists():
            messages.error(request, f"Public key not found: {pub_key_path}")
            return False

        result = run_ssh_copy_id(credential, ssh_password, pub_key_path)

        if result.returncode == 0:
            messages.success(
                request,
                f"Public key installed on {credential.name}! "
                "You can now test the connection.",
            )
        else:
            error = result.stderr.strip()
            messages.error(
                request,
                f"ssh-copy-id failed: {error}",
            )

        return True

    except RemoteCredential.DoesNotExist:
        messages.error(request, "Credential not found")
        return False
    except subprocess.TimeoutExpired:
        messages.error(request, "ssh-copy-id timed out")
        return False
    except FileNotFoundError:
        messages.error(
            request,
            "sshpass not installed. Please install it or copy the public key manually.",
        )
        return False


@login_required
def remote_credentials(request):
    """Remote credentials management page."""
    credentials = RemoteCredential.objects.filter(user=request.user).order_by(
        "-last_used_at", "-created_at"
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            handle_add_remote_credential(request)
        elif action == "delete":
            handle_delete_remote_credential(request)
        elif action == "test":
            handle_test_remote_credential(request)
        elif action == "ssh_copy_id":
            handle_ssh_copy_id(request)

        return redirect("accounts_app:remote_credentials")

    # Check if we just generated a new key pair — show public key
    new_credential_id = request.session.pop("new_credential_id", None)
    new_credential = None
    if new_credential_id:
        new_credential = credentials.filter(id=new_credential_id).first()

    context = {
        "credentials": credentials,
        "new_credential": new_credential,
    }

    return render(request, "accounts_app/remote_credentials.html", context)
