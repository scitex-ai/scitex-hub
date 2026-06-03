# ADR-0003: Prod-stack cutover from `scitex-cloud-prod` to `scitex-hub-prod`

**Status:** Proposed (plan only — do NOT execute until lead+operator sign off in a coordinated session)
**Date:** 2026-06-03
**Supersedes:** none. Follow-up to ADR-0001 (repo-side rename, already complete).
**Owner:** proj-scitex-hub (drafter). Executor: lead, host-side, with operator present.

## 1. Why this ADR exists

ADR-0001 renamed the project end-to-end at the code level (`scitex_cloud` → `scitex_hub`, `scitex-cloud` → `scitex-hub`, `SciTeX Cloud` → `SciTeX Hub`, `SCITEX_CLOUD_*` → `SCITEX_HUB_*`). That work landed in commits `c3c2df407` / `e8e66e173` / `39054f824` / `d38d68947` (May 23, 2026) with a deprecation shim added in `6abb25dcb` (May 24).

**The live prod docker stack on NAS (`DXP480TPLUS-994`) was never cut over.** Today the running containers are still under the `scitex-cloud-prod` compose project name, while `deployment/docker/docker-compose.prod.yml` line 15 declares `name: scitex-hub-prod`. This is the half-done state lead has explicitly flagged: any `docker compose up` against the current repo file would spawn a stray parallel stack, fail on the renamed volumes, and could take the live site down.

This ADR is the **plan** to close that gap in a single coordinated session. **No execution happens against live prod from this PR.**

## 2. Audit: is any repo-side change still needed?

**No.** A full `scitex-dev rename-symbols --dry-run` sweep across four axes confirms zero substantive repo work remains:

| axis | files | matches | verdict |
| --- | --- | --- | --- |
| `scitex-cloud` → `scitex-hub` (kebab) | 15 | 93 | all intentional |
| `scitex_cloud` → `scitex_hub` (snake) | 12 | 56 | all intentional (+6 self-referential collisions) |
| `SciTeX Cloud` → `SciTeX Hub` (display) | 2 | 2 | all intentional |
| `SCITEX_CLOUD_` → `SCITEX_HUB_` (env prefix) | 6 | 48 | all intentional |

The remaining 199 matches fall into four legitimate categories that must NOT be renamed:

1. **Historical record** — `CHANGELOG.md`, `docs/adr/0001-rename-scitex-cloud-to-scitex-hub.md`, `scripts/migrate/rename_to_scitex_hub.sh`. These describe the rename itself; mutating them rewrites history.
2. **Deprecation shims** — `src/scitex_cloud/__init__.py`, `src/scitex_cloud/__main__.py`, `tests/scitex_hub/test_scitex_cloud_shim.py`. The shim's whole purpose is to live at the old import path; renaming it defeats it.
3. **Env-var compat helper** — `config/_env.py`, `config/settings/settings_shared.py`, `tests/config/test_env_legacy_alias.py`. These read both `SCITEX_HUB_*` and the legacy `SCITEX_CLOUD_*` (with `DeprecationWarning`), per ADR-0001 §D.2. Renaming the legacy half breaks the alias.
4. **Different spoke package** — `src/scitex_hub/_skills/scitex-hub-cloud/*.md` describes the standalone `scitex-cloud` PyPI package at `~/proj/scitex-code/cloud`, which is a *different artifact* from this Django web app. Renaming would misdocument it.

There is also one legacy-token compat block in `apps/infra/public_app/config/api_docs.py` (LEGACY_CAMPAIGN_TOKEN_PATTERN). It accepts both `scitex-hub-campaign-*` (current) and `scitex-cloud-campaign-*` (legacy) and emits a `DeprecationWarning`. This must stay until ADR-0001's deprecation window closes (no fixed date yet).

**Conclusion: no `refactor(rename)` PR is needed. This ADR is the only deliverable until the coordinated session.**

## 3. Current live state (as of 2026-06-03)

Verified by lead earlier this session:

- Compose project on host: `scitex-cloud-prod` (NOT `scitex-hub-prod`).
- Containers: `scitex-cloud-prod-django-1`, `…-celery_worker-1`, `…-postgres-1`, `…-redis-1`, `…-gitea-1`, `…-umami-1`, `…-cloudflared-1`, `…-nginx-1`, `…-ws_ssh_proxy-1`, `…-autoheal-1`. (Exact list to be confirmed at session start with `docker compose -p scitex-cloud-prod ps`.)
- Volumes (Docker-namespaced by project):
  - `scitex-cloud-prod_postgres_data` — stateful, large
  - `scitex-cloud-prod_redis_data` — ephemeral cache, discardable
  - `scitex-cloud-prod_gitea_data` — **CRITICAL** (hosts git repos)
  - `scitex-cloud-prod_static_volume` — regenerated on `collectstatic`
  - `scitex-cloud-prod_media_volume` — user uploads, stateful
- Network: `scitex-cloud-prod_scitex-network` (bridge)
- Known broken side-services (per lead this session):
  - `umami` — restart-loop, `28P01 password authentication failed`. Root cause: stale `.env.prod` still uses `SCITEX_CLOUD_POSTGRES_*` legacy names; compose substitutes the now-undefined `${SCITEX_HUB_POSTGRES_*}` to its `:-scitex_2025` default, which doesn't match the volume's stored credentials. (Per PR #234 commit body.)
  - `ws_ssh_proxy` — restart-loop, DNS name-resolution failure. Likely tied to the network-name rename or to umami being down.

`django` itself was rescued by lead (broken `~/.scitex/orochi` symlink replaced + `docker start scitex-cloud-prod-django-1`). The container is now healthy; the site returns 200.

## 4. Target state

Single compose stack with consistent naming:

- Compose project: `scitex-hub-prod`.
- All containers prefixed `scitex-hub-prod-*`.
- All volumes prefixed `scitex-hub-prod_*` with data copied from the old volumes.
- `.env.prod` on host uses only `SCITEX_HUB_*` prefix (no `SCITEX_CLOUD_*`).
- Old volumes retained `read-only` for ≥30 days as cold-rollback.
- ADR-0001's deprecation shims unchanged (still serving legacy import paths and legacy token format).

## 5. Migration steps (host-side, executor = lead)

Each step is reversible. Do NOT abbreviate the backup phase. Order matters.

### 5.1 Pre-flight (T-1h)

```bash
NAS=DXP480TPLUS-994
REPO=/home/ywatanabe/proj/scitex-cloud
BAK=/state/backups/prod-cutover-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$BAK"

# Confirm running stack identity
docker compose -p scitex-cloud-prod ps --format "{{.Names}}\t{{.Status}}\t{{.Image}}" | tee "$BAK/before.ps.txt"
docker volume ls --filter name=scitex-cloud-prod_ | tee "$BAK/before.volumes.txt"

# Snapshot env file
cp -p "$REPO/deployment/docker/envs/.env.prod" "$BAK/.env.prod.snapshot"

# Snapshot compose state
cp -p "$REPO/deployment/docker/docker-compose.prod.yml" "$BAK/docker-compose.prod.yml.snapshot"
cp -p "$REPO/deployment/docker/docker-compose.yml" "$BAK/docker-compose.yml.snapshot"
```

### 5.2 Backups (T-30m) — REQUIRED before any down/up

```bash
# 1. postgres logical dump (small; portable; can restore into any pg version)
docker exec scitex-cloud-prod-postgres-1 \
  pg_dumpall -U "$SCITEX_HUB_POSTGRES_USER" \
  > "$BAK/postgres.sql"
# expect ~tens of MB; gzip if growing

# 2. gitea_data tar (CRITICAL — hosts user git repos)
docker run --rm \
  -v scitex-cloud-prod_gitea_data:/from:ro \
  -v "$BAK":/to alpine \
  tar -C /from -czf /to/gitea_data.tar.gz .

# 3. media_volume tar
docker run --rm \
  -v scitex-cloud-prod_media_volume:/from:ro \
  -v "$BAK":/to alpine \
  tar -C /from -czf /to/media_volume.tar.gz .

# 4. Quick sanity: backup sizes non-trivial
ls -lh "$BAK"/
```

### 5.3 Maintenance mode + announce (T-5m)

Operator posts a Telegram heads-up. nginx already has a 502 shim — when django is stopped, users will see "Service is starting up" automatically.

### 5.4 Cutover (T-0)

```bash
cd "$REPO"

# (a) Stop the old stack cleanly (NOT --volumes; we keep data)
docker compose -p scitex-cloud-prod \
  -f deployment/docker/docker-compose.yml \
  -f deployment/docker/docker-compose.prod.yml \
  down

# (b) Rename .env.prod prefix
sed -i.bak-$(date -u +%Y%m%dT%H%M%SZ) \
  's/^SCITEX_CLOUD_/SCITEX_HUB_/g' \
  deployment/docker/envs/.env.prod

# (c) Clone each named volume from old project to new project
for V in postgres_data redis_data gitea_data static_volume media_volume; do
  docker volume create "scitex-hub-prod_${V}"
  docker run --rm \
    -v "scitex-cloud-prod_${V}":/from:ro \
    -v "scitex-hub-prod_${V}":/to alpine \
    sh -c 'cp -a /from/. /to/'
done

# (d) Verify volume sizes match (sanity)
for V in postgres_data redis_data gitea_data static_volume media_volume; do
  OLD=$(docker run --rm -v "scitex-cloud-prod_${V}":/x alpine du -sb /x | cut -f1)
  NEW=$(docker run --rm -v "scitex-hub-prod_${V}":/x alpine du -sb /x | cut -f1)
  printf "%-22s old=%s new=%s\n" "$V" "$OLD" "$NEW"
done | tee "$BAK/volume-sizes.txt"
# If any size differs unexpectedly, ABORT — see §6.

# (e) Start the new stack
docker compose -p scitex-hub-prod \
  -f deployment/docker/docker-compose.yml \
  -f deployment/docker/docker-compose.prod.yml \
  up -d
```

### 5.5 Smoke tests (T+2m)

```bash
sleep 30   # let init+migrations settle
# Healthz
curl -fsS --max-time 10 http://localhost:8000/healthz/ | jq .
# Public landing
curl -fsSI --max-time 10 https://scitex.ai/ | head -5
# A2A
curl -fsS --max-time 10 https://a2a.scitex.ai/v1/agents/ | jq '.agents | length'
# Gitea
curl -fsS --max-time 10 http://localhost:3000/api/v1/version | jq .
# Umami (should now be healthy because env prefix is fixed)
docker logs --tail 20 scitex-hub-prod-umami-1 2>&1 | grep -iE 'ready|error' | head
# ws_ssh_proxy
docker logs --tail 20 scitex-hub-prod-ws_ssh_proxy-1 2>&1 | tail -5
```

Pass criteria: `/healthz/` returns 200; `https://scitex.ai/` returns 200; A2A returns the agent list; gitea returns a version; umami has "ready" in logs without "28P01".

## 6. Rollback

If §5.5 fails or anything in §5.4(c)-(d) misbehaves:

```bash
# (a) Stop the new stack
docker compose -p scitex-hub-prod \
  -f deployment/docker/docker-compose.yml \
  -f deployment/docker/docker-compose.prod.yml \
  down

# (b) Restore env file
cp "$BAK/.env.prod.snapshot" deployment/docker/envs/.env.prod

# (c) Old volumes were NOT deleted in §5.4 — restart the old project
docker compose -p scitex-cloud-prod \
  -f deployment/docker/docker-compose.yml \
  -f deployment/docker/docker-compose.prod.yml \
  down  # in case any new-stack container is still wedged on old volume
docker compose -p scitex-cloud-prod \
  -f deployment/docker/docker-compose.yml \
  -f deployment/docker/docker-compose.prod.yml \
  up -d
```

Note: rollback works because we *clone* volumes in §5.4(c), not *rename*. The old `scitex-cloud-prod_*` volumes stay intact and reusable.

The only data-loss window is between §5.4(a) (down) and §5.4(e) (up) for writes that arrive during the cutover. Since traffic during a planned window is near-zero (off-peak) and the cutover takes ~2-5 minutes, this is acceptable.

## 7. Cleanup (T+30 days, only on operator sign-off)

```bash
# After ≥30 days of green prod, drop the old volumes + the on-disk backup tarballs
for V in postgres_data redis_data gitea_data static_volume media_volume; do
  docker volume rm "scitex-cloud-prod_${V}"
done
# (Backup tarballs in $BAK can be moved to colder storage at this point.)
```

## 8. Risks + mitigations

| risk | likelihood | impact | mitigation |
| --- | --- | --- | --- |
| `cp -a` mid-write inconsistency on postgres_data | low | high (DB corruption) | §5.4(a) `down` stops postgres first; cp happens against a quiesced volume |
| `cp -a` permissions/ownership drift | low | medium (container can't open files) | `cp -a` preserves mode + owner; sanity check via §5.4(d) |
| umami DB user mismatch (still 28P01) | medium | low (umami down ≠ site down) | env rename in §5.4(b) fixes the prefix; if user still wrong, recreate in postgres before §5.4(e) — see §9 |
| gitea_data tar interrupted | low | high (lose user repos) | §5.2 step 2 is mandatory; if tar exits non-zero, abort entire cutover |
| Cloudflare tunnel attached to old network | low | high (site invisible) | new stack defines its own `scitex-hub-prod_scitex-network`; cloudflared joins automatically because it's in the same compose. Verify with `docker network inspect scitex-hub-prod_scitex-network` after §5.4(e). |
| `.env.prod` has other `SCITEX_CLOUD_*` keys we don't anticipate | medium | low | §5.4(b) sed is comprehensive; backup at §5.4(b) `.bak-…` allows quick diff/revert |
| postgres won't re-initialize on new volume because data dir already populated | low | medium | postgres treats a populated `/var/lib/postgresql/data` as initialized and skips init — that's the desired path |
| docker.sock permissions on new project | low | low | autoheal already mounts `/var/run/docker.sock`; no change |

## 9. Known follow-ups (out of scope for this ADR)

- **umami DB user**: PR #234 documented that the umami `node` process inside its container uses a postgres user/db pair set via `DATABASE_URL` (line 130 of `docker-compose.yml`). If that user does not exist on the existing postgres volume, even after the env rename, `28P01` persists. Plan: after §5.4(e), connect to postgres and either (a) `ALTER USER scitex WITH PASSWORD '<value-from-env>';` or (b) `CREATE USER` if missing. Document in a follow-up issue if needed.
- **`scitex-hub-prod` vs `scitex-cloud-prod` references in scripts**: any operator shell aliases, ops runbooks, monitoring scripts, etc. that reference `scitex-cloud-prod-*` container names must be updated post-cutover. Lead to enumerate during the session.
- **Cloudflare tunnel routing config**: tunnel token is in `.env.prod` (`SCITEX_HUB_CLOUDFLARE_TUNNEL_TOKEN`); the *ingress rules* live in the Cloudflare dashboard — no compose change needed, but lead should sanity-check the dashboard for any hardcoded container names.

## 10. Open questions for lead + operator

1. **Timing**: target session window (off-peak JST evening?).
2. **Backup destination**: `/state/backups/` writeable by ywatanabe? Or use `/home/ywatanabe/backups/`?
3. **`.env.prod` content**: lead to confirm there are no `SCITEX_CLOUD_*` keys *other than* `POSTGRES_*` that we should worry about; if e.g. `SCITEX_CLOUD_GITEA_TOKEN` exists, the sed in §5.4(b) handles it but lead should review the diff before §5.4(e).
4. **Cleanup window**: 30 days OK, or shorter/longer? Drives the storage commitment for kept-old volumes.
5. **Communication**: operator-facing maintenance announcement (Telegram only? Status page?).

## 11. Drafter notes

- proj-scitex-hub does NOT have docker.sock in its sac container; cannot execute §5.x. Drafter role only.
- a2a→lead is currently 403 ACL-deny on NAS sac state.db; relay is via the Claude conversation chain. Lead, please add `grant_send(sender='proj-scitex-hub', target='lead')` so future plan-revisions can come back via a2a without manual relay.
- This document is intentionally heavy on commands rather than prose. The executor (lead) needs runnable copy-paste, not generalities.
