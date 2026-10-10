# Self-Host Deployment Guide

Run the whole hub on your own host — the supported answer for confidential
projects whose data must not leave your infrastructure. This is the same
compose stack the project itself runs; nothing here is a fork or a
"community edition".

## 1. What you get (services)

Base stack (`deployment/docker/docker-compose.yml`): `postgres`
(`postgres:15-alpine`), `pgbouncer` (`edoburu/pgbouncer:v1.25.1-p0`),
`redis` (`redis:7-alpine`), `gitea` (`gitea/gitea:latest`), `umami`
(`ghcr.io/umami-software/umami:postgresql-latest`). Prod overlay
(`deployment/docker/docker-compose.prod.yml`) adds the `django` app
(Daphne ASGI, image built from `deployment/docker/Dockerfile.prod`),
`celery_worker`, `celery_beat`, `nginx`, `cloudflared`, `autoheal`.
Staging overlay (`docker-compose.staging.yml`) is the same shape with debug
ports and **no Docker-socket mount** (removed 2026-08-25, noted in-file).
Start with the staging overlay to rehearse; promote to prod overlay for real
use. Local-staging rehearsal is documented in
`docs/runbooks/local-staging-orochi-cloud.md`.

## 2. Minimal viable host

- Linux x86-64, ~4 vCPU / 16 GB RAM / 100 GB disk (prod compose reserves
  2 G + 2 G + 1 G across django/postgres/redis and limits django to
  8 G — see `docker-compose.prod.yml:44-61,125-130,137-142`).
- Docker engine + compose v2 (checked in the staging runbook pre-flight).
- Public IP **optional**: without it, drop `cloudflared`/`nginx` and serve
  the Django port directly on your LAN/VPN. Cloudflare tunnel is how
  `scitex.ai` is exposed; it is not required for the app to run.
- SLURM **optional**: the stack boots without it; only SLURM-backed code
  execution needs `/etc/slurm/slurm.conf`, `/run/munge`, `/var/log/slurm`
  bind-mounts (listed in the staging file's django volumes).
- Apptainer **optional** (user-code containers): needs `/dev/fuse` and the
  two `security_opt` relaxations documented in
  `docker-compose.staging.yml` under the django service, plus the `.sif`
  built per `deployment/singularity/README.md`.

External dependencies you must provide: a Postgres password, a Django
`SECRET_KEY`, OAuth credentials for login (Google via allauth —
`config/settings/settings_auth.py:85-96`), and DNS/TLS if exposing publicly
(handled by Cloudflare tunnel in the reference deployment).

## 3. Data directories (all on your host — nothing leaves it)

| Data | Container path | Host side | Evidence |
|------|---------------|-----------|----------|
| Postgres | `/var/lib/postgresql/data` | `postgres_data` named volume | `docker-compose.yml:39,182-183` |
| Gitea repos | `/data` | `gitea_data` named volume | `docker-compose.yml:124,186-187` |
| User project files | `/app/data/users` | `${SCITEX_SLURM_USER_DATA_ROOT:-/opt/scitex/data/users}` | prod compose django volumes |
| Uploads | `/app/media` | `media_volume` named volume | `settings_static.py:106` |
| Redis AOF | `/data` | `redis_data` named volume | `docker-compose.yml:111` |

For confidential projects: keep all five on encrypted host storage, do not
attach `cloudflared`, and run your own backups per
`docs/runbooks/backup-restore.md` — the reference deployment has no
scheduled backup to inherit.

## 4. Bring-up

```bash
# 4a. Secrets — prod REFUSES to start without a real DB password
# (settings_prod.py raises ImproperlyConfigured on placeholder/empty).
cp deployment/docker/envs/README.md  # read first: env-file layout
# Fill in deployment/docker/envs/.env.prod (DB password, SECRET_KEY,
# OAuth client id/secret, SCITEX_SLURM_USER_DATA_ROOT for your host).

# 4b. Build + start (staging first).
cd deployment/docker
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --build
curl -f http://localhost:31294/   # staging default port per runbook

# 4c. Promote to prod shape when staging is green.
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
curl -f --max-time 10 http://localhost:8000/healthz/  # prod healthcheck
```

The prod image bakes the repo tree in (`Dockerfile.prod`, verified by
`scripts/deploy/verify_image_dependency_contract.py` per
`docs/deployment/production-image-dependency-gate.md`) — redeploy by
rebuilding, not by editing files inside the container. User data lives in
the volumes/bind-mounts above, so rebuilds do not touch it.

## 5. Confidential-project checklist

1. `cloudflared` service removed or never started; no inbound exposure beyond your network.
2. OAuth app is yours (your Google workspace / your allauth provider) — users authenticate against your IdP, not the project's.
3. `SCITEX_SLURM_USER_DATA_ROOT` points at your encrypted volume.
4. Backup runbook (`docs/runbooks/backup-restore.md`) scheduled on your host.
5. Gitea (`gitea_data`) included in that backup — project git history lives there, not in Postgres alone.

## 6. Limits to know before you commit

- Single-host design: Postgres, Redis, Gitea, and Django all run as
  containers on one machine. There is no multi-node or HA story in this repo.
- No automated backup — see the gap statement in `docs/runbooks/backup-restore.md` §5.
- Docker-socket mount in the **prod** django service (`/var/run/docker.sock`,
  `docker-compose.prod.yml`) is required for current workspace features but
  widens blast radius; staging already removed it. Harden or accept explicitly.
