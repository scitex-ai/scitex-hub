# 06 - Docker Services

## Services

| Service | Port | Purpose |
|---------|------|---------|
| web | 8000 | Django |
| db | 5432 | PostgreSQL |
| redis | 6379 | Cache |
| gitea | 3001 | Git |
| celery_worker | - | Tasks |
| flower | 5555 | Monitor |

## Commands

```bash
# Start
docker compose up -d

# Stop
docker compose down

# Logs
docker compose logs -f web

# Restart
docker compose restart web
```

## Config

`deployment/docker/docker_dev/docker-compose.yml`
