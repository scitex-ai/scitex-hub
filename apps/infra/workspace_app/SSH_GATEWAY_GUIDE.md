# SSH Gateway for SciTeX Cloud Workspaces

## Overview

The SSH Gateway allows users to connect directly to their workspace containers via SSH, providing a native terminal experience without using the web interface.

## Features

- **Django Authentication**: Authenticate using your SciTeX Cloud credentials
- **Automatic Container Management**: Containers are spawned/attached automatically on connection
- **Persistent Sessions**: Your workspace persists across SSH sessions
- **Secure**: Uses SSH protocol with RSA host keys
- **WebSocket Tunnel**: Access via Cloudflare Tunnel - no port forwarding needed!

## Architecture

```
# Production (via Cloudflare Tunnel)
User SSH Client → cloudflared → Cloudflare Tunnel → SSH Gateway → SLURM Container

# Development (direct)
User SSH Client → SSH Gateway (Port 2200) → Django Auth → User Container
```

## Production Usage (Recommended)

### Prerequisites

1. **Install cloudflared**: Download from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
2. **Register SSH key**: Go to https://scitex.ai/accounts/settings/ssh-keys/

### SSH Config Setup

Add to your `~/.ssh/config`:

```bash
Host scitex
  HostName ssh.scitex.ai
  User your-username
  ProxyCommand cloudflared access ssh --hostname %h
```

### Connect

```bash
ssh scitex
```

That's it! No port forwarding, no firewall configuration needed.

---

## Development Setup

### 1. Start the SSH Gateway

Run the SSH gateway management command:

```bash
# Inside the Django container
python manage.py run_ssh_gateway --port 2200 --host 0.0.0.0
```

Or for production with custom host key:

```bash
python manage.py run_ssh_gateway --port 2200 --host-key /app/ssh_keys/ssh_host_rsa_key
```

### 2. Docker Configuration

The SSH gateway port is exposed in docker-compose:

```yaml
ports:
  - "2200:2200"  # SSH gateway for user workspaces
```

### Connecting via SSH (Development)

```bash
# Basic connection (uses default SSH key ~/.ssh/id_rsa)
ssh -p 2200 your-username@127.0.0.1

# Specify a specific key
ssh -p 2200 -i ~/.ssh/scitex_key your-username@127.0.0.1

# Skip host key checking (for development)
ssh -p 2200 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null your-username@127.0.0.1
```

**Note**: Password authentication is disabled. You must use SSH keys.

### Example Session

```bash
$ ssh -p 2200 test-user@127.0.0.1

Welcome to SciTeX Cloud Workspace, test-user!
Container: scitex-workspace-test-user

test-user@abc123:~$ pwd
/home/scitex
test-user@abc123:~$ ls
projects/  data/  code/
test-user@abc123:~$ exit
Connection to 127.0.0.1 closed.
```

## Configuration Options

### Management Command Options

- `--host`: Host to bind SSH server (default: `0.0.0.0`)
- `--port`: Port to listen on (default: `2200`)
- `--host-key`: Path to SSH host key (default: auto-generate)

### Environment Variables

- `SSH_KEY_DIR`: Directory to store SSH keys (default: `/app/ssh_keys`)

## Security Considerations

### Host Key Management

The SSH gateway uses RSA host keys for security:

1. **Auto-generated keys**: Created automatically on first run
2. **Persistent keys**: Stored in `SSH_KEY_DIR` for consistency across restarts
3. **Custom keys**: Can be specified with `--host-key` option

### Authentication

- **Public key authentication only** - Password authentication is disabled for security
- Users must register SSH keys through the web interface (`/accounts/settings/ssh-keys/`)
- Keys are validated against the `WorkspaceSSHKey` model in the database
- Only active users with registered SSH keys can connect
- Failed authentication attempts are logged
- Key usage is tracked (last_used_at timestamp)

### Network Security

- Default port is 2200 (separate from Gitea's 2222 and admin SSH)
- Bind to specific host for production (`--host`)
- Use firewall rules to restrict access

## Port Allocation

SciTeX Cloud uses the following SSH ports:

- **2200**: User workspace SSH gateway (this service)
- **2222**: Gitea SSH for Git operations
- **22**: Host system SSH (if applicable)

## Troubleshooting

### Connection Refused

1. Check if SSH gateway is running:
   ```bash
   ps aux | grep run_ssh_gateway
   ```

2. Verify port is accessible:
   ```bash
   nc -zv localhost 2200
   ```

### Authentication Failures

1. Verify SSH key is registered:
   ```bash
   python manage.py shell
   >>> from django.contrib.auth import get_user_model
   >>> from apps.accounts_app.models import WorkspaceSSHKey
   >>> User = get_user_model()
   >>> user = User.objects.get(username='test-user')
   >>> keys = WorkspaceSSHKey.objects.filter(user=user)
   >>> for key in keys:
   ...     print(f"{key.title}: {key.fingerprint}")
   ```

2. Check SSH key fingerprint matches:
   ```bash
   # Get fingerprint of your local key
   ssh-keygen -lf ~/.ssh/id_rsa.pub
   # Compare with registered key in Django
   ```

3. Check logs for auth attempts:
   ```bash
   tail -f /app/logs/ssh-gateway.log | grep -E "(authentication|Public key)"
   ```

4. Test with verbose SSH output:
   ```bash
   ssh -vvv -p 2200 test-user@127.0.0.1
   ```

### Container Not Starting

1. Check Docker socket access:
   ```bash
   docker ps
   ```

2. Verify UserContainerManager works:
   ```bash
   python manage.py shell
   >>> from apps.workspace_app.services.container_manager import UserContainerManager
   >>> from django.contrib.auth import get_user_model
   >>> User = get_user_model()
   >>> user = User.objects.get(username='test-user')
   >>> manager = UserContainerManager()
   >>> container = manager.get_or_create_container(user)
   >>> print(container.name)
   ```

## Development vs Production

### Development Setup

```bash
# Inside container
python manage.py run_ssh_gateway --port 2200

# Connect from host
ssh -p 2200 test-user@127.0.0.1
```

### Production Setup

#### Cloudflare Tunnel Configuration

1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. Navigate to **Access** → **Tunnels**
3. Select your tunnel (e.g., `scitex-nas`)
4. Add a new **Public Hostname**:
   - **Subdomain**: `ssh`
   - **Domain**: `scitex.ai`
   - **Service Type**: `SSH`
   - **URL**: `django:2200`

This routes `ssh.scitex.ai` directly to the SSH Gateway container.

#### SSH Gateway Service

1. Run SSH gateway as a service (systemd, supervisor, etc.)
2. Use persistent host key
3. Configure firewall rules
4. Set up monitoring and logging
5. Consider using a process manager

Example systemd service:

```ini
[Unit]
Description=SciTeX Cloud SSH Gateway
After=network.target docker.service

[Service]
Type=simple
User=scitex
WorkingDirectory=/app
ExecStart=/usr/local/bin/python manage.py run_ssh_gateway --port 2200 --host 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Monitoring

### Logging

The SSH gateway logs to stdout/stderr and Django's logging system:

```python
# View SSH gateway logs
tail -f /app/logs/django.log | grep -E "(SSHGateway|run_ssh_gateway)"
```

### Metrics to Monitor

- Active SSH connections
- Authentication success/failure rates
- Container spawn/attach times
- Connection duration

## Future Enhancements

Potential improvements:

1. ✅ **Public key authentication**: Implemented - SSH key-based auth is now the only method
2. **Session recording**: Record SSH sessions for auditing
3. **Rate limiting**: Prevent brute force attacks
4. **Session management**: View/terminate active sessions from web UI
5. **SFTP support**: File transfer via SFTP protocol
6. **Port forwarding**: SSH tunneling capabilities
7. **Certificate-based authentication**: Support SSH certificates for advanced key management

## API Reference

### SSHGateway Class

```python
class SSHGateway(paramiko.ServerInterface):
    """SSH server interface for user authentication."""

    def check_auth_password(username: str, password: str) -> int:
        """Authenticate against Django user database."""

    def check_channel_request(kind: str, chanid: int) -> int:
        """Verify channel request is allowed."""

    def check_channel_shell_request(channel: paramiko.Channel) -> bool:
        """Handle shell request and spawn container."""
```

### SSHKeyManager Class

```python
class SSHKeyManager:
    """Manage SSH host keys."""

    def load_or_generate_host_key() -> paramiko.RSAKey:
        """Load existing key or generate new one."""

    def get_host_key_fingerprint(host_key: paramiko.RSAKey) -> str:
        """Get SHA256 fingerprint of host key."""
```

## Resources

- [Paramiko Documentation](https://www.paramiko.org/)
- [SSH Protocol RFC 4253](https://tools.ietf.org/html/rfc4253)
- [Django Authentication](https://docs.djangoproject.com/en/stable/topics/auth/)

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review logs in `/app/logs/`
3. Open an issue on GitHub
4. Contact support@scitex.ai

---

Last updated: 2026-01-06
