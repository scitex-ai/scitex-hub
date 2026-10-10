# Data-Protection Operations Note

Maps each line of the operator's ISMS direction (2026-10-10: professional
service, data-protection/backup explicit, self-host for confidential
projects, ISO/IEC 27001-based ISMS) to the hub mechanism that actually
implements it — with the code file as evidence for every claim. Where no
mechanism exists, it says so and points at the ask.

## (a) Data protection and backup operations are explicit

| ISMS expectation | Hub mechanism (evidence) | Status |
|------------------|--------------------------|--------|
| Backup/restore procedure exists | `docs/runbooks/backup-restore.md` — manual pg_dump + volume tar + user-data rsync, with verify steps | PROCEDURE, manual |
| Scheduled backups | None — `backup_database.sh` (manual `pg_dump` wrapper) and `backup_workspaces.sh` (rsync snapshotter, cron line is a commented example) exist but nothing schedules them: no crontab/timer/beat entry, no compose mount of `/app/backups` (see runbook intro); `backupCount` in `settings_logging.py` is log rotation only | GAP — ask §5 of the runbook |
| Restore rehearsal | Staging exists as the rehearsal surface (`docs/runbooks/local-staging-orochi-cloud.md`); no recorded rehearsal | GAP — rehearse + log |
| Media/object durability | `FileSystemStorage` at `MEDIA_ROOT` on `media_volume` (`settings_static.py:71-76,106`); durable only insofar as the host volume is | PARTIAL — in backup scope, no replication |
| Git history durability | `gitea_data:/data` volume + Gitea metadata in shared Postgres (`docker-compose.yml:121-152`) | PARTIAL — in backup scope |
| Redis persistence | `--appendonly yes` (`docker-compose.prod.yml:136`) — crash durability for sessions/cache, not a backup | EXPLICIT NON-BACKUP |

## (b) Self-hosted version supported for confidential projects

| ISMS expectation | Hub mechanism (evidence) | Status |
|------------------|--------------------------|--------|
| Self-host guide | `docs/deployment/self-host.md` — compose services, data dirs, bring-up, confidential checklist | DONE (this PR) |
| Single-tenant data confinement | All five data stores are host-local volumes/bind-mounts (`docker-compose.yml` volumes block; `SCITEX_SLURM_USER_DATA_ROOT` bind); no SaaS dependency in the data path | TRUE by construction |
| Confidential deployment shape | Drop `cloudflared`/`nginx`, own OAuth app, own encrypted disks — §5 checklist in the self-host guide | PROCEDURE |
| No HA/multi-node story | All stateful services co-located on one host; no replication config in repo | LIMIT — stated in guide §6 |

## (c) Operations aligned to ISO/IEC 27001-based ISMS

| Control area | Hub mechanism (evidence) | Status |
|--------------|--------------------------|--------|
| Access control — interactive login | Google OAuth via allauth (`config/settings/settings_auth.py:85-96`); session + `AuthenticationMiddleware` + `OnSiteAuthMiddleware` (`settings_middleware.py:10-30`, `apps/infra/project_app/middleware.py`) | LIVE |
| Access control — programmatic | Workspace JWT, 60-min TTL (`settings_auth.py:172-174`), `Authorization: Bearer` resolved by `JWTBearerToSessionMiddleware` (`apps/infra/accounts_app/middleware.py`); no passwords for OAuth accounts (`docs/runbooks/publish-app-from-user-account.md` §2) | LIVE |
| Access control — secrets hygiene | Prod/staging refuse placeholder/empty DB passwords at startup (`settings_prod.py` `ImproperlyConfigured` raise; `settings_staging.py` equivalent) | LIVE |
| Isolation — per-user file jails | `ALLOWED_DATA_ROOT=/app/data/users` with component-wise containment `_is_within`/`_resolve_safe` (`src/scitex_hub/project/_mcp/handlers.py:21-80`) + Django twin `validate_path_in_project` (`apps/infra/project_app/services/filesystem/permissions.py:36`); traversal/`..`/null-byte rejection, 404-not-403 on violation | LIVE |
| Isolation — project session binding | `AuthenticatedProjectSessionMiddleware` binds `current_project_slug` only when `request.user.username` owns the namespace (`apps/infra/project_app/middleware.py:15-42`) | LIVE |
| Isolation — execution sandbox (in flight) | Apptainer SIF user-code container (`deployment/singularity/README.md`, `deployment/docs/05_APPTAINER_CONTAINERS.md`); rootless notes + minimal `security_opt`/device grants in `docker-compose.staging.yml`; FigRecipe container pilot running on a sibling track | PILOT — not yet the default execution path |
| Least privilege — staging socket removal | Docker-socket mount removed from staging 2026-08-25 (noted in `docker-compose.staging.yml`); prod django still mounts `/var/run/docker.sock` | PARTIAL — prod exception documented in self-host §6 |
| Availability — health supervision | Per-service healthchecks (django `healthz`, postgres `pg_isready`, redis ping — compose files) + `autoheal` container restarts (prod overlay) | LIVE |
| Availability — dependency integrity | Prod image dependency-floor gate (`docs/deployment/production-image-dependency-gate.md`, `scripts/deploy/verify_image_dependency_contract.py`) | LIVE |
| Logging/monitoring | Structured logging settings (`settings_logging.py`); storage canary runbook is stage-1 plan, not live monitoring (`docs/deployment/storage-canary-runbook.md`) | PARTIAL |

## Honest summary for the ISMS file

Authentication, per-user file jailing, secret hygiene, and health
supervision are implemented and evidenced above. Self-hosting is documented
and true by construction (host-local data path). Execution sandboxing is a
pilot, not the default. **Automated backup does not exist** — the runbook
makes operator-run backup possible today, and its §5 lists the five infra
asks (scheduled pg_dump, volume snapshots, user-data replication,
rehearsal record, optional PITR) that must land before any control
worksheet may mark backup "implemented".
