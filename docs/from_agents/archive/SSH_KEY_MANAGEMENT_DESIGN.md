<!-- ---
!-- Timestamp: 2025-10-18 23:45:00
!-- Author: ywatanabe (designed with Claude)
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/SSH_KEY_MANAGEMENT_DESIGN.md
!-- --- -->

# SSH Key Management System for SciTeX Cloud

## Overview
Provide secure, user-specific SSH keys for Git operations (clone, push, pull) with external services like GitHub, GitLab, Bitbucket.

## Architecture

### Key Generation Levels

#### 1. User-Level SSH Key (Recommended for MVP)
**One key pair per user account**

**Pros:**
- Simple to manage
- User registers one public key across all their Git services
- Single point of management
- Matches GitHub's user-level SSH key model

**Cons:**
- If compromised, affects all repositories
- Can't revoke access to specific projects

**Storage:**
- Private key: `~/.ssh/scitex_user_{user_id}_rsa`
- Public key: `~/.ssh/scitex_user_{user_id}_rsa.pub`
- Or: `/home/ywatanabe/proj/scitex-cloud/data/ssh_keys/user_{user_id}/id_rsa`

#### 2. Project-Level SSH Key (Future Enhancement)
**One key pair per project**

**Pros:**
- Granular access control
- Revoke access per project
- Better security isolation
- Matches GitHub's Deploy Keys model

**Cons:**
- More complex to manage
- User must register multiple keys
- More database records

**Storage:**
- Private key: `/data/{username}/proj/{project_slug}/.ssh/id_rsa`
- Public key: `/data/{username}/proj/{project_slug}/.ssh/id_rsa.pub`

#### 3. Service-Level SSH Key (Optional)
**Different keys for GitHub, GitLab, etc.**

**Pros:**
- Service isolation
- Fine-grained revocation

**Cons:**
- Very complex
- User burden increases

---

## Recommended Implementation: User-Level Keys

### Database Schema

**Option A: Store in UserProfile model**
```python
# apps/workspace_app/models.py
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # ... existing fields ...

    # SSH Key Management
    ssh_public_key = models.TextField(blank=True, null=True)
    ssh_key_fingerprint = models.CharField(max_length=100, blank=True, null=True)
    ssh_key_created_at = models.DateTimeField(null=True, blank=True)
    ssh_key_last_used_at = models.DateTimeField(null=True, blank=True)
```

**Option B: Separate SSH Key model (more flexible)**
```python
# apps/workspace_app/models.py
class SSHKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ssh_keys')
    name = models.CharField(max_length=100)  # e.g., "SciTeX Cloud - Main"
    public_key = models.TextField()
    fingerprint = models.CharField(max_length=100, unique=True)
    private_key_path = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Optional: Project-level keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = [['user', 'name']]
```

### SSH Key Manager

```python
# apps/workspace_app/ssh_manager.py
import os
import subprocess
from pathlib import Path
from typing import Tuple, Optional
from django.contrib.auth.models import User

class SSHKeyManager:
    """Manage SSH keys for Git operations."""

    def __init__(self, user: User):
        self.user = user
        self.ssh_dir = Path(settings.BASE_DIR) / 'data' / 'ssh_keys' / f'user_{user.id}'

    def get_or_create_user_key(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Get or create SSH key pair for user.

        Returns:
            (success, public_key_content, error_message)
        """
        private_key_path = self.ssh_dir / 'id_rsa'
        public_key_path = self.ssh_dir / 'id_rsa.pub'

        # Check if key already exists
        if private_key_path.exists() and public_key_path.exists():
            try:
                public_key = public_key_path.read_text()
                return True, public_key, None
            except Exception as e:
                return False, None, str(e)

        # Create SSH directory
        self.ssh_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Generate new key pair
        try:
            subprocess.run([
                'ssh-keygen',
                '-t', 'rsa',
                '-b', '4096',
                '-C', f'{self.user.email or self.user.username}@scitex.ai',
                '-f', str(private_key_path),
                '-N', '',  # No passphrase for automation
            ], check=True, capture_output=True)

            # Set proper permissions
            private_key_path.chmod(0o600)
            public_key_path.chmod(0o644)

            # Read public key
            public_key = public_key_path.read_text()

            # Get fingerprint
            fingerprint_result = subprocess.run([
                'ssh-keygen',
                '-lf', str(public_key_path)
            ], capture_output=True, text=True)
            fingerprint = fingerprint_result.stdout.strip()

            # Update user profile or SSHKey model
            from .models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=self.user)
            profile.ssh_public_key = public_key
            profile.ssh_key_fingerprint = fingerprint
            profile.ssh_key_created_at = timezone.now()
            profile.save()

            return True, public_key, None

        except subprocess.CalledProcessError as e:
            return False, None, f"Failed to generate SSH key: {e.stderr}"
        except Exception as e:
            return False, None, str(e)

    def get_private_key_path(self) -> Optional[Path]:
        """Get path to user's private SSH key."""
        private_key_path = self.ssh_dir / 'id_rsa'
        return private_key_path if private_key_path.exists() else None

    def delete_user_key(self) -> Tuple[bool, Optional[str]]:
        """Delete user's SSH key pair."""
        try:
            import shutil
            if self.ssh_dir.exists():
                shutil.rmtree(self.ssh_dir)

            # Update database
            from .models import UserProfile
            try:
                profile = UserProfile.objects.get(user=self.user)
                profile.ssh_public_key = None
                profile.ssh_key_fingerprint = None
                profile.ssh_key_created_at = None
                profile.save()
            except UserProfile.DoesNotExist:
                pass

            return True, None
        except Exception as e:
            return False, str(e)
```

### Updated Git Clone with SSH Support

```python
# apps/workspace_app/directory_manager.py (update clone_from_git method)
def clone_from_git(self, project: Project, git_url: str, use_ssh: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Clone a Git repository with SSH or HTTPS.

    Args:
        project: Project instance
        git_url: Git repository URL
        use_ssh: If True, use SSH key for authentication
    """
    try:
        import subprocess
        project_path = self.get_project_path(project)
        if not project_path or not project_path.exists():
            return False, "Project directory not found"

        # Prepare environment for SSH
        env = os.environ.copy()

        if use_ssh:
            from .ssh_manager import SSHKeyManager
            ssh_manager = SSHKeyManager(self.user)
            private_key_path = ssh_manager.get_private_key_path()

            if not private_key_path:
                # Fall back to HTTPS
                use_ssh = False
            else:
                # Use GIT_SSH_COMMAND to specify SSH key
                env['GIT_SSH_COMMAND'] = f'ssh -i {private_key_path} -o StrictHostKeyChecking=accept-new'

        # Clone the repository
        result = subprocess.run(
            ['git', 'clone', git_url, str(project_path)],
            capture_output=True,
            text=True,
            timeout=300,
            env=env
        )

        if result.returncode == 0:
            return True, None
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            return False, error_msg

    except Exception as e:
        return False, str(e)
```

### UI Components

#### 1. User Settings - SSH Keys Section

**Location:** `/settings/ssh-keys/` or `/dashboard/ssh-keys/`

**UI Elements:**
```html
<!-- apps/profile_app/templates/profile_app/ssh_keys.html -->

<div class="ssh-keys-section">
    <h2>SSH Keys</h2>
    <p>SSH keys allow you to clone and push to Git repositories without passwords.</p>

    {% if ssh_public_key %}
    <!-- Existing Key -->
    <div class="ssh-key-card">
        <div class="key-header">
            <h3>SciTeX Cloud SSH Key</h3>
            <span class="key-fingerprint">{{ ssh_key_fingerprint }}</span>
        </div>

        <div class="key-content">
            <pre><code>{{ ssh_public_key }}</code></pre>
            <button onclick="copySSHKey()" class="btn btn-sm btn-outline-primary">
                📋 Copy Public Key
            </button>
        </div>

        <div class="key-instructions">
            <h4>How to use this key:</h4>
            <ol>
                <li>Copy the public key above</li>
                <li>Add it to your Git hosting service:
                    <ul>
                        <li><a href="https://github.com/settings/keys" target="_blank">GitHub → Settings → SSH Keys</a></li>
                        <li><a href="https://gitlab.com/-/profile/keys" target="_blank">GitLab → Preferences → SSH Keys</a></li>
                        <li><a href="https://bitbucket.org/account/settings/ssh-keys/" target="_blank">Bitbucket → Settings → SSH Keys</a></li>
                    </ul>
                </li>
                <li>Use SSH URLs when cloning (e.g., <code>git@github.com:user/repo.git</code>)</li>
            </ol>
        </div>

        <div class="key-info">
            <p>Created: {{ ssh_key_created_at|date:"Y-m-d H:i" }}</p>
            {% if ssh_key_last_used_at %}
            <p>Last used: {{ ssh_key_last_used_at|date:"Y-m-d H:i" }}</p>
            {% endif %}
        </div>

        <button onclick="deleteSSHKey()" class="btn btn-sm btn-danger">
            🗑️ Delete Key
        </button>
    </div>
    {% else %}
    <!-- No Key Yet -->
    <div class="no-key-message">
        <p>You don't have an SSH key yet.</p>
        <button onclick="generateSSHKey()" class="btn btn-primary">
            🔑 Generate SSH Key
        </button>
    </div>
    {% endif %}
</div>
```

#### 2. Project Clone Form Updates

```html
<!-- When "Clone from Git" is selected -->
<div id="git_clone_options">
    <div class="form-group">
        <label>Clone Method</label>
        <div class="radio-group">
            <input type="radio" name="clone_method" value="ssh" id="clone_ssh" checked>
            <label for="clone_ssh">
                SSH (Recommended)
                {% if not has_ssh_key %}
                <span class="badge badge-warning">No SSH key configured</span>
                {% endif %}
            </label>

            <input type="radio" name="clone_method" value="https" id="clone_https">
            <label for="clone_https">HTTPS (Public repos only)</label>
        </div>
    </div>

    {% if not has_ssh_key %}
    <div class="alert alert-info">
        <strong>SSH key required</strong>
        <p>To clone private repositories securely, please <a href="/settings/ssh-keys/">set up your SSH key</a> first.</p>
    </div>
    {% endif %}
</div>
```

### Views

```python
# apps/profile_app/views.py

@login_required
def ssh_keys(request):
    """SSH key management page."""
    from apps.workspace_app.ssh_manager import SSHKeyManager

    ssh_manager = SSHKeyManager(request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'generate':
            success, public_key, error = ssh_manager.get_or_create_user_key()
            if success:
                messages.success(request, 'SSH key generated successfully!')
            else:
                messages.error(request, f'Failed to generate SSH key: {error}')

        elif action == 'delete':
            success, error = ssh_manager.delete_user_key()
            if success:
                messages.success(request, 'SSH key deleted successfully!')
            else:
                messages.error(request, f'Failed to delete SSH key: {error}')

        return redirect('profile_app:ssh_keys')

    # GET request
    profile = request.user.profile
    context = {
        'ssh_public_key': profile.ssh_public_key,
        'ssh_key_fingerprint': profile.ssh_key_fingerprint,
        'ssh_key_created_at': profile.ssh_key_created_at,
        'ssh_key_last_used_at': profile.ssh_key_last_used_at,
    }
    return render(request, 'profile_app/ssh_keys.html', context)


@login_required
@require_http_methods(["POST"])
def api_generate_ssh_key(request):
    """API endpoint to generate SSH key."""
    from apps.workspace_app.ssh_manager import SSHKeyManager

    ssh_manager = SSHKeyManager(request.user)
    success, public_key, error = ssh_manager.get_or_create_user_key()

    if success:
        return JsonResponse({
            'success': True,
            'public_key': public_key
        })
    else:
        return JsonResponse({
            'success': False,
            'error': error
        }, status=400)
```

## Security Considerations

1. **Private Key Protection**
   - Store in secure directory with 0o600 permissions
   - Never expose via web interface
   - Backup strategy for key loss

2. **No Passphrase**
   - Required for automated Git operations
   - Trade-off: convenience vs security
   - Mitigated by server-level access controls

3. **Key Rotation**
   - Allow users to regenerate keys
   - Old key is deleted, new key generated
   - User must update Git services

4. **Audit Trail**
   - Track when keys are created
   - Track when keys are used (update `last_used_at` on git operations)
   - Log key deletion events

## Implementation Phases

### Phase 1: MVP - User-Level SSH Keys
- [x] Design architecture (this document)
- [ ] Add SSH key fields to UserProfile model
- [ ] Implement SSHKeyManager class
- [ ] Create SSH key management UI
- [ ] Update Git clone to use SSH
- [ ] Add instructions for registering keys

### Phase 2: Enhanced Features
- [ ] Project-level SSH keys (deploy keys)
- [ ] Multiple keys per user
- [ ] Key expiration/rotation policies
- [ ] Email notifications on key events

### Phase 3: Advanced
- [ ] Integration with GitHub/GitLab APIs to auto-register keys
- [ ] GPG signing keys
- [ ] Hardware security key support (YubiKey)

## Benefits

1. **Security**: No passwords/tokens in Git URLs
2. **Convenience**: One-time setup, works for all repos
3. **Private Repos**: Full access to user's private repositories
4. **Standard Practice**: Matches GitHub/GitLab workflows
5. **Audit Trail**: Know when keys are used

## Open Questions

1. Should we support both user-level and project-level keys simultaneously?
2. Should we provide key backup/export functionality?
3. Should we integrate with Git service APIs to auto-add keys?
4. Should we support ED25519 keys (newer, faster) in addition to RSA?

<!-- EOF -->
