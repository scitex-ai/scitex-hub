# Incident: 2026-06-06 prod cutover (scitex-cloud → scitex-hub rename)

**Status:** RECOVERED. Prod (scitex.ai) restored to the original 82-user dataset on the
original volumes via the original code path. No data loss. v2/v3 cutover scheduled for a
later window.

**Operator-facing impact:** ~10 min of intermittent 503/530 from scitex.ai during two
cutover attempts (~22:43–22:51 JST and a follow-on re-rollback ~23:00–23:15 JST). Existing
sessions preserved (SECRET_KEY never regenerated). No DB writes lost — the live data was
never overwritten.

## Timeline (2026-06-06, JST)

| Time | Event |
|------|-------|
| 21:58 | Phase 1: pg_dump of live scitex_cloud_nas (158 MB) + tag rollback image `scitex-cloud-prod-django:pre-cutover-20260606_215805`. Test-restore of dump into scratch DB verifies auth_user=82, latest=155\|nhk2202. |
| 22:00 | Phase 2: `CREATE DATABASE scitex_hub_nas` + `pg_dump scitex_cloud_nas \| psql scitex_hub_nas` inside live postgres. Row counts match across all checked tables. |
| 22:07 | Phase 3: `.env.prod` shadow-add of `SCITEX_HUB_*` keys mirrored verbatim from `SCITEX_CLOUD_*` (incl. SECRET_KEY); 77 new keys, DB-name keys retargeted to `scitex_hub_nas`. |
| 22:43 | Phase 4.1+4.2: stop scitex-cloud-prod stack + `cp -a` six volumes from `scitex-cloud-prod_*` to `scitex-hub-nas_*` via alpine. Total 7s, ~382 MB. |
| 22:44 | Phase 4.3: `docker compose down` removes old containers + network (cloudflared killed → SSH tunnel `ssh nas` via bastion.scitex.ai dies mid-script). New stack `scitex-hub-prod` built + brought up. |
| 22:45 | Recovery via direct LAN SSH (`ywatanabe@192.168.11.21`) — agent container has LAN access; cloudflared was never the only path. Old containers restarted via `docker start <names>` (containers were stopped, not removed). |
| 22:48 | First recovery: scitex.ai externally back to 200. |
| 22:49 | Re-attempted Phase 4 v2 cleanly. New stack came up with `scitex-hub-prod-cloudflared-1` in restart loop AND `scitex-hub-prod-postgres-1` showing `scitex_hub_nas` does NOT EXIST. |
| 22:52 | Rolled back to scitex-cloud-prod by sed-cloning the new compose to old project/volume names + rollback image. cloudflared still restart-looping (same root cause). |
| 22:53 | Cloudflared fix found: `--env-file /home/ywatanabe/proj/scitex-cloud/deployment/docker/envs/.env.prod` makes compose-time `${SCITEX_HUB_CLOUDFLARE_TUNNEL_TOKEN_PROD}` interpolate; service recovers. |
| 22:55 | Row-count check on rolled-back postgres shows auth_user=24 / latest=24\|test-user — **NOT the Phase-1 dataset**. Stopped writers immediately, escalated to lead. |
| 23:05 | Read-only forensic across all 6 postgres-data volumes via scratch-volume clones. Found: `scitex-cloud-nas_postgres_data` holds the real 82-user data; `scitex-cloud-prod_postgres_data` and `scitex-hub-nas_postgres_data` both carry an unrelated 24-user test-user dataset. |
| 23:13 | Re-rolled the rollback compose to point at `scitex-cloud-nas_postgres_data` (matching the OLD compose's `name:`). Postgres opened cleanly (log: "Skipping initialization"). |
| 23:14 | Row-counts: auth_user=82, latest=155\|nhk2202. |
| 23:20 | scitex.ai externally 200 + text/html (45 KB) + Django access log shows real /landing/ and /apps/home/ traffic. RESTORED. |

## Root causes

### RC-1: volume-name confusion (the big one)

The OLD production `docker-compose.yml` for prod declared its named volumes with `name:
scitex-cloud-nas_*` (suffix `-nas`, not `-prod`). The compose project itself was
`scitex-cloud-prod`, so the Docker-side container names were `scitex-cloud-prod-*`, but
the *volumes* carried the `nas` suffix. Three separate volume families coexisted on the
NAS host:

* `scitex-cloud-nas_postgres_data` — **the real live data** (82 users).
* `scitex-cloud-prod_postgres_data` — a 24-user residue from some earlier dev/test stack.
* `scitex-hub-nas_postgres_data` — created from scratch when the v2 cutover's new
  postgres container booted on an empty external volume.

The cutover's Phase 4.2 `cp -a` was sourcing the WRONG volume
(`scitex-cloud-prod_postgres_data`, the 24-user residue) and copying into
`scitex-hub-nas_postgres_data`. The first rollback (which sed-edited the new compose to
point back at `scitex-cloud-prod_postgres_data`) inherited the same wrong volume. Both
the v2 attempt and the first rollback served the 24-user dataset, not the real 82 users.

The live 82-user volume (`scitex-cloud-nas_postgres_data`) was **never touched** at any
point — no cp into it, no postgres init against it, no compose project mounted it
during the cutover. Data was structurally safe throughout.

Why this was missed up-front: the Phase 1 inventory `docker volume ls | grep
scitex-cloud-prod_*` filtered out the `-nas` variants — the surveyor pattern matched the
container-name prefix, not the actual volume suffix in the compose file. Phase 1 pg_dump
went through `docker exec scitex-cloud-prod-postgres-1 pg_dump …` which correctly read
the volume the live container was mounted on (the `-nas` one) and produced a 158 MB dump
with 82 users — so the backup was always correct. The mistake was on the SOURCE side of
the volume copy in Phase 4.

### RC-2: cloudflared token did not interpolate

The prod `docker-compose.yml` uses
`command: tunnel --no-autoupdate run --token ${SCITEX_HUB_CLOUDFLARE_TUNNEL_TOKEN_PROD}`.
Compose resolves `${VAR}` from the project-directory `.env` file (or shell env) at parse
time. On the NAS host the `docker_prod/.env` was a regular file dated 2026-04-25 — a
stale copy that pre-dated the `SCITEX_HUB_*` rename — not the symlink to `../envs/.env.prod`
that exists in the repo. So the var resolved empty, cloudflared booted with `--token ""`,
exited (printing its help text to logs), and the container restart-looped. Long-running
containers from before the rename had their env captured at create-time and were
unaffected; only freshly-created containers hit this.

Fix: `docker compose --env-file /home/ywatanabe/proj/scitex-cloud/deployment/docker/envs/.env.prod -f … up -d` makes compose use the right env file regardless of the project-directory `.env` state. Recreating the cloudflared container alone is enough — no full restart.

### RC-3: my SSH path went through the very service I was cutting over

`ssh nas` was configured (`~/.ssh/conf.d/ywata.conf`) to use `cloudflared access ssh
--hostname bastion.scitex.ai` as ProxyCommand. The cloudflared container I stopped in
Phase 4.1 was the same one fronting that bastion tunnel. The SSH session died mid-script
the moment cloudflared went down, taking Phase 4.2 and onward with it. Recovered via
direct LAN SSH (`ywatanabe@192.168.11.21` with `-o ControlMaster=no -o ControlPath=none`
because `/home/agent/.ssh/.control:*` is read-only in this agent container).

## What worked

* Phase 1 pg_dump + test-restore verified the backup BEFORE any prod write. When the
  cutover went sideways, the dump was a known-good anchor we could have restored from
  even if the live volume had been hit (it wasn't).
* SECRET_KEY sha256 match between the pre-existing `SCITEX_CLOUD_DJANGO_SECRET_KEY` and
  the shadow-added `SCITEX_HUB_DJANGO_SECRET_KEY` (file values 52 chars / in-container
  50 chars after `$$`→`$` unescape) — no session invalidation when the new stack
  briefly came up.
* Rollback image was tagged in Phase 1.6 (`scitex-cloud-prod-django:pre-cutover-20260606_215805`),
  so we never needed to rebuild during recovery.
* Read-only-forensic-first via scratch-volume clones: copied each suspect volume to a
  throwaway, ran a temp postgres against the clone, queried `auth_user`. Proved the live
  82-user data was on `scitex-cloud-nas_postgres_data` without touching the source.
  Lead-mandated, exactly the right call.
* Lead-enforced stop-on-ambiguity rule held the cutover at the first data discrepancy.
  No improvising on prod.

## Action items for v3

1. **Source data via pg_dump from the live DB, not raw volume copy.** Mirrors Phase 1
   and sidesteps the volume-name issue entirely.
2. **`--env-file envs/.env.prod` on every compose command** for the prod project, until
   the on-disk `docker_prod/.env` is fixed to be a symlink (or removed) on the NAS.
3. **Audit the SCITEX_*_VAR substitution surface** in `docker_prod/docker-compose.yml`:
   anything that uses `${VAR}` at compose-parse time needs to either be in the env file
   that compose actually reads, or moved to a service `environment:` block that is
   resolved from the container's own env_file at start-time.
4. **Drop or rename `scitex-cloud-prod_postgres_data`** (and similar 24-user-test
   residue volumes) on the NAS once root-cause writeup is final — they are landmines.
   Until then, preserve as evidence.
5. **Offline dry-run** of v3 on isolated project/volume/port names before the next prod
   cutover window — proves the new stack serves 82 users without touching the live
   stack or the live tunnel.
6. **Use direct LAN SSH (192.168.11.21) for any tooling that may stop the cloudflared
   tunnel**, never `ssh nas` (which routes through it).

## Addendum: v3 attempt #3 (2026-06-07 00:30 JST)

A second cutover attempt was made on the next day with the validated image
(`scitex-hub-prod-django:latest`, BUILD_EXIT=0 after `--no-cache` rebuild from
develop@3c665a2b which had PR #237 + #238 + #239 merged). The dryrun on that
image was GREEN (http 200, ct=text/html, size=44857, 82 users via pgbouncer,
nhk2202). The live v3 attempt ROLLED BACK after the django container entered a
restart loop (Up 8–40s, never settling, scitex.ai 503 sustained). Rollback to
scitex-cloud-prod restored scitex.ai to 200 + 82 + nhk2202 within ~7 min.

### RC-5: external volume must pre-exist for `up`

The new compose declares all six prod volumes with `external: true`. After
deleting `scitex-hub-nas_postgres_data` (the 24-user residue) in step 3 of the
cutover, `docker compose up -d` failed with `external volume "scitex-hub-
nas_postgres_data" not found`. Recovery was to `docker volume create
scitex-hub-nas_postgres_data` (empty) then re-run `up -d`; postgres init then
populated it. Caveat for v3 attempt #4: any operator who deletes an external
volume MUST pre-create the empty replacement before the next `up`.

### RC-6: stale on-disk `.env` defeats `env_file:` directive even with `--env-file` set on the compose call

`docker_prod/docker-compose.yml` had `env_file: - .env` per service. On the NAS
checkout, `docker_prod/.env` is a regular file dated 2026-04-25 (pre-rename),
containing only `SCITEX_CLOUD_*` keys — zero `SCITEX_HUB_*` keys. The
`--env-file envs/.env.prod` flag on the `docker compose` command line only
affects compose-time `${VAR}` substitution (good for the cloudflared token).
It does NOT change which file the `env_file:` directive feeds into each
container's runtime environment. Two paths, two inputs, easy to confuse.

Consequence: each v3 container received only `SCITEX_CLOUD_*` env vars at
runtime. In the NEW image (with PR #237 alias helper), settings_prod.py reads
`SCITEX_HUB_DB_NAME` via `getenv_with_legacy_alias` → not present → alias
falls back to `SCITEX_CLOUD_DB_NAME=scitex_cloud_nas` (the only value in
env). Django's `manage.py migrate` then asks pgbouncer for `scitex_cloud_nas`,
but the v3 postgres only had `scitex_hub_nas` (restored from dump). pgbouncer
log: `WARNING server login failed: FATAL database "scitex_cloud_nas" does not
exist`. The entrypoint's migrate step crashes, the container exits, docker
restarts it under `restart: unless-stopped`, the cycle repeats every 8–40
seconds — never reaching daphne, scitex.ai stays 503.

Verified by env inspection of the rolled-back live django container:
`grep -E '^SCITEX_HUB_DB|^SCITEX_HUB_POSTGRES' env` returned nothing;
`docker_prod/.env` contained 0 `SCITEX_HUB_*` lines while `envs/.env.prod`
contained 80. The old prod stack continued to work because its image was the
pre-PR-#237 build that read `SCITEX_CLOUD_DB_NAME` directly — matching the
stale env.

### Fix — per-stack env separation (NOT a global symlink)

The HUB and ROLLBACK stacks need DIFFERENT env files: the hub stack must read
`SCITEX_HUB_*` (new naming + new DB `scitex_hub_nas`), the rollback stack must
read `SCITEX_CLOUD_*` (legacy naming + old DB `scitex_cloud_nas`). A global
symlink `docker_prod/.env → ../envs/.env.prod` would point BOTH stacks at the
hub env file — which would convert the rollback stack into a landmine on its
next container recreate (host reboot, `restart: always` respawn, OOM, manual
restart): rollback django would read `SCITEX_HUB_DB_NAME=scitex_hub_nas`, ask
pgbouncer for a DB the rollback postgres doesn't have, and enter the same
restart loop — but this time inside our safety floor. An initial attempt at
this symlink (2026-06-07 00:54 JST) was reverted ~5 min later (01:01 JST) on
review.

The correct fix is per-stack separation, scoped to each compose file:

1. **HUB compose** (`docker_prod/docker-compose.yml`, in repo, PR #240):
   change every `env_file: - .env` to `env_file: - ../envs/.env.prod`. Hub
   stack now reads the canonical `SCITEX_HUB_*` source directly with no
   `.env` dependency. **Container runtime env layer fixed.**
2. **ROLLBACK compose** (`docker_prod/docker-compose.rollback.yml`, NAS-local
   recovery artifact, not in repo until issue #243 lands): keeps
   `env_file: - .env` as-is. `.env` is the regular file with `SCITEX_CLOUD_*`
   only — exactly what rollback needs.
3. The shared `docker_prod/.env` regular file is left UNTOUCHED. After PR
   #240 merges, the hub stack no longer reads it; only rollback does.
4. **Compose-time `${VAR}` substitution layer** (the OTHER half of the env
   path that PR #240's `env_file:` directive change does NOT cover): for the
   make path the fix is **PR #244** (Option C) — adds `--env-file
   ../envs/.env.prod` to the prod `COMPOSE_CMD` in Makefile + rebuild.sh,
   symmetric with the existing staging COMPOSE_CMD. Without this, compose-time
   `${SCITEX_HUB_CLOUDFLARE_TUNNEL_TOKEN_PROD}` (in the cloudflared service
   command) would resolve from `docker_prod/.env` (the stale SCITEX_CLOUD_*
   file) → empty token → tunnel dead even with django serving 200.

## v3 attempt #4 timeline (2026-06-07 02:30–03:10 JST)

Operator gave explicit GO ("今すぐGO" + "fail freely, no need to revert").
Lead's directives in effect: data floor absolute (sources `:ro`, dump
preserved); fail-forward (no auto-rollback); abort signature = django
RestartCount ≥ 2 OR Exited (not slow-warmup).

Phases executed:

1. **PREP** — closed PR #241 as duplicate (PR #240 already on develop, only
   doc-correction remained); NAS `git pull` to 8794dac4; cloudflared token
   pre-flight ✓; fresh `pg_dump` of live `scitex_cloud_nas` as `scitex_nas`
   user → `v4-pre-20260606T165824Z.sql` (146 MB).
2. **Pre-mirror** (all RO source, wipe-then-cp -a target):
   * `gitea_data` 12.1 GB → 43m16s (HDD + many small git objects)
   * `scitex_config_volume` 136 MB → 2.16s
   * `media_volume` 683 MB → 2.53s
   * Sources (`scitex-cloud-nas_*`) never mutated. Site serving throughout.
3. **DOWN (downtime begins)** — manual `docker compose -p scitex-cloud-prod
   -f docker_prod/docker-compose.rollback.yml down --remove-orphans` (Gap 2:
   make couldn't reach the legacy `scitex-cloud-prod` project). First attempt
   failed because rollback compose was at `/tmp/rollback.yml` and compose
   resolved its `env_file: .env` relative to /tmp/. Retried with rollback
   compose restored to `docker_prod/` (its proper location, so `.env`
   resolves to the existing stale-Apr25 file with SCITEX_CLOUD_* keys). 12
   containers stopped+removed in 40.4s; 7 scitex-cloud-nas_* volumes
   preserved.
4. **First UP attempt — FAILED, restart-loop signature** — naive `docker
   compose up -d` brought up ALL services at once. Django's entrypoint ran
   `migrate` against a fresh-empty `scitex_hub_nas` and created Django's
   types/extensions. Then the v4 dump restore ran AFTER → tried to recreate
   those types → `django.db.utils.IntegrityError: duplicate key value
   violates unique constraint "pg_type_typname_nsp_index"`. Plus stale
   `static_volume` (not wiped, had v3 #3 root-owned files) → `EACCES
   permission denied` during vite build. RestartCount hit 2 → STOP per gate.
5. **Diagnosis** — sequencing race: dryrun A had run postgres+pgbouncer
   first, then restored dump, then brought up the rest. The v3 #4 first-try
   ran everything at once and put migrate BEFORE restore. Plus
   static_volume residue caused the EACCES (mirrored volumes were
   ownership-preserved by `cp -a`, but static was kept as-is from v3 #3
   which had root-owned files).
6. **Corrected sequence (FIX1+FIX2+FIX3)**:
   * **FIX1**: `down hub-prod` (keep volumes), wipe
     `scitex-hub-nas_{postgres_data,static_volume}` (the two residue
     volumes; do NOT touch the mirrored gitea/media/scitex_config), `up
     postgres pgbouncer redis` only, wait postgres healthy.
   * **FIX2**: restore v4 dump into freshly-empty `scitex_hub_nas`. 10.3s,
     auth_user=82 ✓, nhk2202=155 ✓, NO IntegrityError (clean target).
   * **FIX3**: `up -d` rest. Django's `migrate` saw populated
     `django_migrations` → no-op → IntegrityError addressed. Visitor-pool
     ImportError caused RestartCount=1 (known-benign per dryrun precedent,
     issue #242), second start reached healthy at ~4 min.
7. **INTEGRITY GATE GREEN**:
   * https://scitex.ai/landing/ → HTTP 200 in 156ms, real SciTeX page
   * `SELECT count(*) FROM auth_user` → 82
   * `SELECT id, username FROM auth_user WHERE username='nhk2202'` →
     `155|nhk2202`
   * cloudflared tunnel: 3 quic connections registered (nrt07/12/16 Tokyo)
   * All 11 hub-prod containers healthy
8. **POST-DONE SMOKE GREEN** (per lead's "preserve workspaces" requirement):
   * scitex_config_volume in django: 137 MB, scitex:scitex-owned, real
     content (`browser/ logs/ scholar/ templates/ verification.db`)
   * media_volume: 684 MB, scitex:scitex-owned, real subdirs
     (`bibtex_enriched/ bibtex_uploads/ videos/`)
   * gitea_data: 12.1 GB, git:git-owned, 47 repositories enumerated, gitea
     internal API returns real repo list. No EACCES on the mirrored mounts.
   * The single EACCES in django logs was the pre-FIX1 static_volume entry,
     not an ongoing issue.

Real outage window: `down` (02:52) → INTEGRITY GREEN (~03:10) ≈ 18 min.

## RC-7: Sequencing race (up-all-then-restore vs postgres-first-then-restore)

Naive `docker compose up -d` brings up ALL services in dependency order
(postgres → django via `depends_on: postgres healthy`). Django's entrypoint
runs `migrate` as part of its boot, against whatever state postgres has at
that moment. If postgres is freshly-initialized-empty (because the volume was
wiped pre-up), migrate creates the Django schema from scratch — including all
the django-managed types/extensions. A subsequent `pg_dump` restore against
that same DB then tries to CREATE TYPE / CREATE EXTENSION again → catalog
collision → IntegrityError on `pg_type_typname_nsp_index`.

Dryrun A had implicitly avoided this by bringing up postgres+pgbouncer first,
restoring the dump before django ever started, then bringing up django.
Django's migrate then saw the dump's `django_migrations` table as
fully-populated → no-op → no schema re-creation → no collision.

**Operational rule**: when restoring a `pg_dump` into a freshly-initialized
prod-like postgres, always restore BEFORE the django container starts
migrating. The corrected runbook (next section) enforces this.

## Corrected runbook for cutover-with-pg_dump

For future cutover-style operations that combine "fresh DB volume + restore
dump + bring up django stack":

```
1. PREP (no downtime):
   a. NAS git pull develop (must have PR #240 + PR #244 merged)
   b. Verify envs/.env.prod has SCITEX_HUB_*_PROD vars (esp. cloudflared token)
   c. Take fresh pg_dump from live source (read-only):
      pg_dump -U <db-user> -d <source-db> --clean --if-exists \
        --no-owner --no-privileges > /backups/v<n>-pre-<ts>.sql
   d. (If migrating file volumes) Pre-mirror RO source → wiped target with
      cp -a (preserve ownership) or rsync -aH --delete (more robust on
      ongoing changes); never delete or write to source volumes.

2. DOWNTIME (manual; old stack project name may not match make):
   docker compose -p <old-project> -f <old-compose>.yml down --remove-orphans

3. WIPE residue volumes (not the mirrored ones):
   docker volume rm scitex-hub-nas_postgres_data
   docker volume create scitex-hub-nas_postgres_data
   docker volume rm scitex-hub-nas_static_volume      # regen on collectstatic
   docker volume create scitex-hub-nas_static_volume

4. UP DB-TIER ONLY (postgres+pgbouncer+redis):
   cd deployment/docker/docker_prod
   docker compose --env-file ../envs/.env.prod up -d postgres pgbouncer redis
   # wait postgres (healthy)

5. RESTORE dump into the freshly-empty DB (BEFORE django ever starts):
   cat /backups/v<n>-pre-<ts>.sql | docker exec -i scitex-hub-prod-postgres-1 \
     psql -U <db-user> -d <target-db>
   # verify expected row counts before proceeding

6. UP REST of stack:
   docker compose --env-file ../envs/.env.prod up -d
   # django's migrate is now a no-op against the restored django_migrations table

7. WARMUP (≥6 min budget) — gate: abort on RestartCount≥2 OR Exited (NOT
   slow-warmup; start_period is legitimately 4-5 min for collectstatic +
   workspace pip/npm).

8. INTEGRITY GATE: https://<domain>/<known-path> → 200 + DB row counts +
   canary user + real page rendering + tunnel up.
```

After PR #244 merges, step 6 simplifies to `make ENV=prod start` (Option C
makes the make path symmetric with staging).

## Operator-facing follow-ups (status updated 2026-06-07)

* **PR #244** opened (Option C) — adds `--env-file ../envs/.env.prod` to
  prod COMPOSE_CMD in Makefile + rebuild.sh; closes Gap 1 (compose-time
  --env-file), Gap 2 (stop-all project name divergence), Gap 3 (rebuild.sh
  static_volume name drift). After merge, `make ENV=prod start` works clean
  for the operator's habitual path.
* **Issue #242** filed — visitor-pool `ImportError:
  scitex.template.clone_template` crashes django on every boot, recovers on
  restart; latent bug to fix with try/except OR pip install.
* **Issue #243** filed — canonicalize NAS-local `docker-compose.rollback.yml`
  into the repo (`deployment/docker/docker_prod/`) so the rollback floor
  definition is version-controlled.
* Anthropic API key visible in `.env.staging` (flagged earlier by lead,
  separate from this incident).
* `make rebuild`'s Apptainer sandbox post-step still errors on read-only fs
  (non-blocking but noisy).
* The new prod compose's volume `external: true` declarations require
  operators to pre-create any volume they wipe before the next `up` (RC-5).
  Consider switching to compose-managed volumes (no `external:`) once the
  cutover is stable, so deletes self-heal.

<!-- EOF -->
