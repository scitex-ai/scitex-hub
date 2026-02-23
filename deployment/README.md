# Deployment

## Quick Start

```bash
make ENV=dev start      # Start development
make ENV=prod start     # Start production
make status             # Check what's running
```

## Structure

```
deployment/
├── docker/           # Docker Compose configs and Dockerfiles
│   ├── docker-compose.yml           # Base config
│   ├── docker-compose.prod.yml      # Production overrides
│   ├── docker-compose.staging.yml   # Staging overrides
│   ├── Dockerfile.prod              # Production image
│   ├── envs/                        # Environment files
│   └── common/                      # Shared scripts (entrypoint, nginx)
├── slurm/            # SLURM cluster configuration
├── singularity/      # User workspace containers
├── host-setup/       # Host machine setup scripts
├── envs/             # Environment templates
└── docs/             # Additional documentation
```

## Commands

| Command | Description |
|---------|-------------|
| `make ENV=<env> start` | Start environment |
| `make ENV=<env> stop` | Stop environment |
| `make ENV=<env> rebuild` | Stop, rebuild images, start |
| `make ENV=<env> build` | Build images only (no restart) |
| `make ENV=<env> logs` | View logs |
| `make ENV=<env> shell` | Django shell |
| `make stop-all` | Stop all environments |

## Zero-Downtime Build Strategy

Build new images while containers are running, then quick swap:

```bash
# 1. Build images in background (containers keep running)
make ENV=prod build

# 2. Quick swap: stop old, start new (minimal downtime)
make ENV=prod stop && make ENV=prod start
```

## Config

`SECRETS/.env.{dev,prod}`

---

## Docker Reference

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Image** | Blueprint/template (immutable) |
| **Container** | Running instance of an image |
| **Layer** | Each Dockerfile instruction creates a layer; layers are cached |
| **Volume** | Persistent storage that survives container restarts |
| **Network** | Virtual network for container communication |
| **Health check** | Periodic test to verify container is working |

### Useful Commands

```bash
# Container inspection
docker ps                                    # List running containers
docker ps -a                                 # Include stopped containers
docker logs <container> --tail 50            # View recent logs
docker logs <container> -f                   # Follow logs live
docker exec -it <container> bash             # Shell into container
docker inspect <container>                   # Full container config (JSON)

# Image inspection
docker images                                # List images
docker history <image>                       # Show layer sizes
docker image prune                           # Remove unused images

# Resource monitoring
docker stats                                 # Real-time CPU/memory usage
docker system df                             # Disk usage summary

# Debugging
docker exec <container> curl localhost:8000  # Test internal connectivity
docker cp <container>:/path/file ./local     # Copy file from container
```

### Dockerfile Anatomy (Dockerfile.prod)

```dockerfile
# Multi-stage build: build dependencies separately, copy only what's needed
FROM python:3.11-slim AS python-builder  # Stage 1: Build
FROM python:3.11-slim AS runtime         # Stage 2: Runtime (smaller)

# Each RUN creates a layer - combine commands to reduce layers
RUN apt-get update && apt-get install -y pkg1 pkg2 \
    && rm -rf /var/lib/apt/lists/*       # Clean up in same layer

# COPY creates layers too - order matters for cache efficiency
COPY requirements.txt .                   # Changes rarely → early
COPY src/ ./src/                          # Changes often → late

# ENTRYPOINT vs CMD
ENTRYPOINT ["/entrypoint.sh"]            # Always runs
CMD ["daphne", "..."]                    # Default args, can override
```

### Docker Compose Patterns (docker-compose.prod.yml)

```yaml
services:
  django:
    # Health check: Docker monitors container health
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz/"]
      interval: 30s      # Check every 30s
      timeout: 15s       # Fail if no response in 15s
      retries: 3         # Mark unhealthy after 3 failures
      start_period: 300s # Grace period for startup

    # Resource limits: Prevent runaway memory usage
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 2G

    # Dependencies: Start order control
    depends_on:
      postgres:
        condition: service_healthy  # Wait for healthy, not just started

  # Autoheal: Restart unhealthy containers automatically
  autoheal:
    image: willfarrell/autoheal
    environment:
      AUTOHEAL_CONTAINER_LABEL: all
      AUTOHEAL_INTERVAL: 60
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

### Why Builds Are Slow

1. **No cache** (`--no-cache`): Downloads everything fresh
2. **Heavy dependencies**: CUDA, PyTorch, OpenCV = multi-GB downloads
3. **Layer invalidation**: Change early layer → rebuild all subsequent layers

**Speed up builds:**
```bash
# Use BuildKit cache mounts
RUN --mount=type=cache,target=/root/.cache/pip pip install ...

# Order Dockerfile: stable deps first, changing code last
COPY requirements.txt .    # Stable
RUN pip install -r ...     # Cached if requirements unchanged
COPY src/ ./src/           # Changes often, comes last
```

### Troubleshooting

| Problem | Solution |
|---------|----------|
| Container unhealthy but running | Check `docker logs`; may need autoheal |
| Out of disk space | `docker system prune -a` |
| Container can't connect to host | Use `host.docker.internal` or `extra_hosts` |
| Permission denied in volume | Check UID/GID mapping between host and container |
| Zombie processes accumulating | Use `tini` as PID 1 (init system) |

### Resources

- [Official Docker Docs](https://docs.docker.com/get-started/)
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
