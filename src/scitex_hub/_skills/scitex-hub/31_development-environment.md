---
description: |
  [TOPIC] Development Environment
  [DETAILS] Docker-based development environment — start/stop, container names, hot reload, access URLs, test user..
tags: [scitex-hub-development-environment]
---

# Development Environment

## Docker-Based Development
All development runs in Docker containers. Never run Django directly on host.

## Start/Stop Commands
```bash
make env=dev start       # Start development
make env=dev stop        # Stop
make env=dev restart     # Restart
make env=dev status      # Status
```

## Container Names
Project name `scitex-hub-dev` (set in `deployment/docker/docker_dev/docker-compose.yml`):
- `scitex-hub-dev-django-1` — Main Django app
- `scitex-hub-dev-postgres-1` — PostgreSQL database
- `scitex-hub-dev-redis-1` — Redis cache
- `scitex-hub-dev-gitea-1` — Git hosting
- `scitex-hub-dev-celery_worker-1` — Background tasks
- `scitex-hub-dev-celery_beat-1` — Scheduled tasks

## Running Django Commands
```bash
docker exec scitex-hub-dev-django-1 python manage.py migrate --settings=config.settings.settings_dev
docker exec -it scitex-hub-dev-django-1 python manage.py shell --settings=config.settings.settings_dev
```

## Hot Reload
- **Django**: Auto-reloads on Python file changes
- **TypeScript/CSS**: Vite HMR — edit `.ts` -> Vite detects -> HMR to browser (~200ms)
- **Templates**: Auto-reloads via django-browser-reload

Vite dev server runs on port 5173 inside Docker.

## Default local access URLs

These host ports are defaults. The `SCITEX_HUB_*_PORT_DEV` values in the
development environment can override them.

- Main app: http://127.0.0.1:8000
- Gitea: http://127.0.0.1:3001
- Vite HMR: http://127.0.0.1:5173

Flower is not a managed service in this development Compose definition.
Optional Flower installation and startup are outside this guide's verified scope.

## Environment Files

Development Compose reads `deployment/docker/docker_dev/.env`, conventionally
linked to `../envs/.env.dev`. Configure the real values before starting services;
a clean Git checkout does not contain those private files. The tracked
`deployment/docker/envs/.env.example` is a placeholder template, not a ready
runtime configuration. See [environment configuration](../../../../deployment/docker/envs/README.md).

The canonical staging/production wrapper uses
`deployment/docker/envs/.env.staging` and `.env.prod`, respectively.
Use `scripts/deploy/compose.sh dev ps` from the repository root to inspect the
development service set after configuring its environment.

## Test User
For testing: `test-user`. The password is printed by `init_test_user` on first run; set `SCITEX_HUB_TEST_USER_PASSWORD` to choose it yourself.

## Console Debugging
Browser console interceptor is active in dev mode:
- Prefixes logs with source file and timestamp
- Saves to `./logs/console.log`
- View live: `tail -f ./logs/console.log`

### Log Patterns
```typescript
console.log('[ModuleName] Loaded');
console.log('[ModuleName] functionName:', param1);
console.error('[ModuleName] Error:', error.message, error);
```
