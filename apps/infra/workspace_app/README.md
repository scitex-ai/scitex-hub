# Workspace App

User computational workspace management for SciTeX Cloud.

## Overview

This app manages Docker containers that provide isolated computational environments for users. Each user gets their own container with:

- Python 3.11 + scientific packages (numpy, pandas, matplotlib, etc.)
- Their project data mounted at `/home/user`
- Resource limits (CPU, memory)
- Network access to other SciTeX services

## Components

### Models (`models.py`)
- `UserWorkspace`: Tracks container state for each user

### Services (`services/container_manager.py`)
- `UserContainerManager`: Core service for container lifecycle management
  - `get_or_create_container(user)`: Spawn or attach to user's container
  - `stop_container(user)`: Stop container
  - `exec_command(user, command)`: Execute command in container
  - `cleanup_idle_containers()`: Stop idle containers

### Management Commands
- `python manage.py cleanup_idle_containers`: Stop idle containers (run via cron)

## Usage

### Programmatic Access

```python
from apps.workspace_app.services import UserContainerManager
from django.contrib.auth.models import User

# Get manager
manager = UserContainerManager()

# Get or create user's container
user = User.objects.get(username='ywatanabe')
container = manager.get_or_create_container(user)

# Execute command
exit_code, output = manager.exec_command(user, ["python", "-c", "print('Hello')"])

# Stop container
manager.stop_container(user)
```

### Management Commands

```bash
# Stop idle containers (30 min default)
python manage.py cleanup_idle_containers

# Custom idle timeout
python manage.py cleanup_idle_containers --idle-minutes 60

# Dry run (just list idle containers)
python manage.py cleanup_idle_containers --dry-run
```

## Container Image

The user workspace image must be built before use:

```bash
# Build image
./scripts/deployment/build_user_workspace_image.sh

# Or manually
docker build -t scitex-hub-shared-v0.1.0:latest \
  -f deployment/docker/Dockerfile.user-workspace .
```

## Resource Limits

Default limits per container:
- CPU: 2 cores (200,000 quota)
- Memory: 8 GB
- Idle timeout: 30 minutes

These can be adjusted in `services/container_manager.py`.

## Data Persistence

User data is stored in `/app/data/users/{username}/` on the host and mounted to `/home/user` in the container. Data persists even when containers are stopped or removed.

## Monitoring

Check container status:

```python
manager = UserContainerManager()
status = manager.get_container_status(user)
print(status)  # {'id': '...', 'status': 'running', ...}
```

List idle containers:

```python
idle = manager.list_idle_containers(idle_minutes=30)
for user, container in idle:
    print(f"{user.username}: idle")
```

## Integration Points

This app is designed to be used by:

1. **SSH Gateway** (future): Users SSH in, container spawns
2. **Codespace** (future): Web-based VS Code in container
3. **JupyterLab** (future): Jupyter notebook server in container

## Future Enhancements

- [ ] SSH gateway integration
- [ ] Web UI for container management
- [ ] VS Code server (Codespace)
- [ ] JupyterLab integration
- [ ] Resource usage monitoring dashboard
- [ ] Per-user disk quotas
- [ ] Auto-scaling with container pool

## Architecture

See documentation:
- `docs/SSH_ARCHITECTURE.md`: Overall SSH architecture
- `docs/USER_SSH_FEASIBILITY_ANALYSIS.md`: Feasibility analysis
- `docs/USER_SSH_CONTAINER_IMAGE.md`: Container image details
- `docs/USER_SSH_IMPLEMENTATION_ROADMAP.md`: Implementation plan

## Testing

```python
# Django shell
python manage.py shell

from apps.workspace_app.services import UserContainerManager
from django.contrib.auth.models import User

user = User.objects.get(username='test-user')
manager = UserContainerManager()

# Test container creation
container = manager.get_or_create_container(user)
print(f"Created: {container.name}")

# Test command execution
exit_code, output = manager.exec_command(user, ["python", "--version"])
print(output)

# Test cleanup
manager.stop_container(user)
```

<!-- EOF -->
