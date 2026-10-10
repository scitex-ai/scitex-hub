# Runbook — Backup and Restore

**Status: procedures are MANUAL. No scheduled backup exists in this repo
today.** The only `backup*` settings in the codebase are log-rotation
`backupCount` values (`config/settings/settings_logging.py`,
`settings_dev.py`, `settings_prod.py`, `settings_staging.py`) — they rotate
log files, they do not back up data. A repo-wide grep for
`pg_dump|pgbackrest|barman|restic|borg|cron.*dump` returns no backup job,
only a one-line `pg_dump` hint echoed by
`deployment/docker/common/monitoring/postgres_check_status.sh:173` and test
fixtures using the word "snapshot". Treat everything below as operator-run
commands, and the §5 gap list as the infra asks required before any
"backups are automatic" claim may be made.

## 1. Durable-state inventory (what must be backed up)

| # | State | Mechanism / location | Evidence |
|---|-------|---------------------|----------|
| 1 | Hub PostgreSQL (users, projects, JWT/session rows, celery-beat schedule) | `postgres:15-alpine` container, data in named volume `postgres_data:/var/lib/postgresql/data` | `deployment/docker/docker-compose.yml:36-54,182-183`; engine pinned by `config/settings/settings_shared.py:349` + per-env overrides (`settings_prod.py:144,214`, `settings_staging.py:125`, `settings_dev.py:270`); Postgres-only rule in `docs/adr/0004-postgresql-is-the-only-database-engine.md` |
| 2 | Gitea git repos + metadata | Named volume `gitea_data:/data`; Gitea stores its metadata **in the same Postgres** (`GITEA__database__DB_TYPE: postgres`, host `postgres:5432`) | `deployment/docker/docker-compose.yml:121-152` |
| 3 | User project files | Host directory bind-mounted at `/app/data/users`, default host path `${SCITEX_SLURM_USER_DATA_ROOT:-/opt/scitex/data/users}` | `deployment/docker/docker-compose.prod.yml:63`, `docker-compose.staging.yml:59`; jail root default `/app/data/users` in `src/scitex_hub/project/_mcp/handlers.py:21` |
| 4 | Uploaded media | Named volume `media_volume:/app/media` (`MEDIA_ROOT = base_dir / "media"`, `FileSystemStorage`) | `deployment/docker/docker-compose.yml:188-190`; `config/settings/settings_static.py:71-76,106` |
| 5 | Collected static | Named volume `static_volume:/app/staticfiles` — **rebuildable** via `collectstatic`, back up only to speed restore | compose files; hashing backend `config/storage.py` via `settings_static.py:76` |
| 6 | `.scitex` / `.apps` config + sibling checkouts | Named volumes `scitex_config_volume:/app/.scitex`, `apps_volume:/app/.apps` — **rebuildable** (re-clone/re-install), low value | `docker-compose.prod.yml:56-57,414-417` |
| 7 | Redis | `redis:7-alpine`, `redis_data:/data`, `--appendonly yes` — AOF is crash durability, **not a backup**; sessions/cache only | `docker-compose.yml:109-114`, `docker-compose.prod.yml:135-136` |

Out of scope for this runbook: NAS-side storage (`docs/deployment/storage-canary-runbook.md`
is a stage-1 plan, not live data), external CrossRef/OpenAlex SQLite files
(mounted read-only from the host), Cloudflare tunnel state (recreatable).

## 2. Manual backup (operator-run, today)

Run from the deployment host, in `deployment/docker/`:

```bash
# 2a. Database — consistent logical dump through the compose network.
# DB/user names come from ./envs/.env.prod (or .env.staging); the service
# name below must match the compose project in use.
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  exec -T postgres pg_dump -U "$SCITEX_HUB_POSTGRES_USER" \
  "$SCITEX_HUB_POSTGRES_DB" | gzip > "/backup/scitex-hub-db-$(date +%F).sql.gz"

# 2b. Named volumes (gitea_data, media_volume). Stop writers first
# (django + gitea) to avoid torn copies; postgres_data is covered by 2a
# while the DB is running — do NOT copy its data dir live.
docker compose -f docker-compose.yml -f docker-compose.prod.yml stop django gitea
docker run --rm \
  -v scitex-hub-prod_gitea_data:/src/gitea:ro \
  -v scitex-hub-prod_media_volume:/src/media:ro \
  -v /backup:/dst alpine \
  tar -czf "/dst/scitex-hub-volumes-$(date +%F).tar.gz" -C /src .
docker compose -f docker-compose.yml -f docker-compose.prod.yml start django gitea

# 2c. User files — host bind-mount, copy with any host tool (example rsync).
rsync -a --delete "${SCITEX_SLURM_USER_DATA_ROOT:-/opt/scitex/data/users}/" \
  /backup/scitex-users-$(date +%F)/
```

Verify each artifact before trusting it: `gzip -t` the dump and
`pg_restore --list` (or `psql` trial restore on staging), `tar -tzf` the
archive, and record byte sizes + sha256 in the ops log. An unverified
backup is not a backup.

## 3. Restore

```bash
# 3a. Database. Point of no return — snapshot the live volume first.
docker compose -f docker-compose.yml -f docker-compose.prod.yml stop django celery_worker celery_beat gitea
gunzip -c /backup/scitex-hub-db-YYYY-MM-DD.sql.gz | \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  exec -T postgres psql -U "$SCITEX_HUB_POSTGRES_USER" "$SCITEX_HUB_POSTGRES_DB"

# 3b. Volumes.
docker run --rm \
  -v scitex-hub-prod_gitea_data:/dst/gitea \
  -v scitex-hub-prod_media_volume:/dst/media \
  -v /backup:/src:ro alpine \
  sh -c 'tar -xzf /src/scitex-hub-volumes-YYYY-MM-DD.tar.gz -C /dst'

# 3c. User files — reverse the rsync, then restart and probe.
rsync -a /backup/scitex-users-YYYY-MM-DD/ "${SCITEX_SLURM_USER_DATA_ROOT:-/opt/scitex/data/users}/"
docker compose -f docker-compose.yml -f docker-compose.prod.yml start django celery_worker celery_beat gitea
curl -f http://localhost:8000/healthz/   # same probe as the compose healthcheck
```

Practice restores belong on **staging** (`docs/runbooks/local-staging-orochi-cloud.md`),
never on prod. A restore procedure that has never been rehearsed is a draft.

## 4. What "done" looks like per incident

1. Which artifact (date + sha256) was restored, and why that generation.
2. `healthz` green + login + one project page render (Django + DB + static agree).
3. Gitea reachable and one clone works (git data + DB metadata agree).
4. One user-file read through the hub (bind-mount + jail agree).

## 5. Gap statement — required infra asks (nothing here exists yet)

1. **Scheduled `pg_dump`** (nightly cron/systemd timer on the NAS host, retention ≥ 30 d, off-host copy). Today: §2a by hand.
2. **Volume snapshots** for `gitea_data` / `media_volume` (filesystem or scheduled `tar`). Today: §2b by hand.
3. **User-data replication** (`/opt/scitex/data/users` has no second copy named anywhere in the repo). Today: §2c by hand.
4. **Restore rehearsal record** (dated staging-restore log). Today: none.
5. **PITR/WAL archiving** if RPO < 24 h is ever required (would need a `postgres -c archive_command` change + WAL store; current prod command at `docker-compose.prod.yml:124` sets only `max_connections`/`shared_buffers`).

Until these land, service copy must say "operator-run backups" and never
"automated backup".
