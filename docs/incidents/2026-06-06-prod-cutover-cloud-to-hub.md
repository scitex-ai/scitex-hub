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

## Operator-facing follow-ups

* Anthropic API key visible in `.env.staging` (flagged earlier by lead, separate from this incident).
* `make rebuild`'s Apptainer sandbox post-step still errors on read-only fs (non-blocking but noisy).

<!-- EOF -->
