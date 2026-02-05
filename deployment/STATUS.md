<!-- ---
!-- Timestamp: 2025-11-28 13:43:42
!-- Author: ywatanabe
!-- File: /ssh:ywatanabe@nas:/home/ywatanabe/proj/scitex-cloud/deployment/STATUS.md
!-- --- -->

# Server Status Page

URL: https://scitex.ai/server-status/

## Environment Variables (Required)

Single source of truth: `SECRET/.env.{ENV}`

| Variable                            | Description             |
|-------------------------------------|-------------------------|
| `SCITEX_CLOUD_VISITOR_POOL_SIZE`          | Number of visitor slots |
| `SCITEX_CLOUD_SSH_PORT_{ENV}`       | SSH gateway port        |
| `SCITEX_CLOUD_GITEA_SSH_PORT_{ENV}` | Gitea SSH port          |

## Source Code

| File                                                      | Purpose                              |
|-----------------------------------------------------------|--------------------------------------|
| `apps/public_app/views.py:625`                            | `server_status()` - Main view        |
| `apps/public_app/views.py:1051`                           | `server_status_api()` - API endpoint |
| `apps/public_app/templates/public_app/server_status.html` | HTML template                        |
| `apps/project_app/services/visitor_pool.py:42`            | `POOL_SIZE` definition               |
| `deployment/docker/docker_prod/docker-compose.yml`        | Docker healthcheck definitions       |

## What It Shows

### 1. System Metrics (Real-time Charts)

Host computer metrics (all processes, not just SciTeX).

| Metric       | Description                                       |
|--------------|---------------------------------------------------|
| CPU          | Processor load (%)                                |
| Memory       | RAM usage (%)                                     |
| Disk         | Storage usage (%)                                 |
| GPU          | Graphics load (if available)                      |
| Disk I/O     | Read/write speed                                  |
| Network I/O  | Upload/download speed                             |
| Visitor Pool | Available slots (X / `$SCITEX_CLOUD_VISITOR_POOL_SIZE`) |
| Active Users | Logged-in users                                   |

### 2. Docker Services (9 containers)

Containers managed by docker-compose. Health determined by Docker's built-in healthcheck.

| Service         | Purpose          | Health Check Command                                    |
|-----------------|------------------|---------------------------------------------------------|
| Django          | Web app server   | `curl http://localhost:8000/`                           |
| Nginx           | Reverse proxy    | `curl http://localhost:80/`                             |
| Db (PostgreSQL) | Database         | `pg_isready -U $USER -d $DB`                            |
| Redis           | Cache            | `redis-cli ping`                                        |
| Celery Worker   | Background tasks | `python -c "import redis; redis.Redis('redis').ping()"` |
| Celery Beat     | Scheduled tasks  | `python -c "import redis; redis.Redis('redis').ping()"` |
| Flower          | Celery monitor   | `curl http://localhost:5555/`                           |
| Gitea           | Git server       | `curl http://localhost:3000/`                           |
| Cloudflared     | HTTPS tunnel     | `cloudflared version`                                   |

### 3. Infrastructure

Services checked by socket connection or command execution.

| Service     | Purpose           | Health Check                                        |
|-------------|-------------------|-----------------------------------------------------|
| SSH Gateway | Workspace access  | TCP connect to `$SCITEX_CLOUD_SSH_PORT_{ENV}`       |
| Gitea SSH   | Git operations    | TCP connect to `$SCITEX_CLOUD_GITEA_SSH_PORT_{ENV}` |
| SLURM       | Job scheduler     | `sinfo` returns partitions                          |
| Apptainer   | Secure containers | `apptainer --version` succeeds                      |

## How Health Is Defined

```
Healthy (Green)
├── Docker: container.status == "running" AND health_status == "healthy"
├── SSH: socket.connect() returns 0 (port open)
├── Database: SELECT 1 succeeds
├── Redis: cache.set/get works
├── SLURM: sinfo returns exit code 0 with output
└── Apptainer: apptainer --version returns exit code 0

Unhealthy (Red)
├── Docker: container stopped OR health_status == "unhealthy"
├── SSH: socket.connect() fails (port closed)
├── Database: query fails
├── Redis: cache operation fails
├── SLURM: sinfo fails or returns empty
└── Apptainer: command not found or fails

Starting (Orange)
└── Docker: health_status == "starting" (within start_period)
```

## Troubleshooting

```bash
# Check logs
docker logs scitex-cloud-prod-django-1

# Restart service
docker restart scitex-cloud-prod-django-1

# Full rebuild
make ENV=prod build && make ENV=prod restart
```

<!-- EOF -->