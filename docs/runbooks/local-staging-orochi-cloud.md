<!-- ---
!-- Timestamp: 2026-06-13
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-hub/docs/runbooks/local-staging-orochi-cloud.md
!-- --- -->

# Runbook — Local staging env for orochi-cloud

## Goal

Stand up a **local** SciTeX Hub staging environment on a developer
workstation, optionally with the SciTeX Orochi orchestrator co-running
beside it, and walk through trying the webapp via port-forward —
without touching the NAS, production, or any shared service.

This runbook is **descriptive**, not invocative: it documents the
sequence and the safety rails. A human (or a separately-authorised
agent) executes the commands; this document explains what each step
does, what to check, and how to back out.

> **Read first** before running anything. Items marked **STOP** require
> explicit approval from the project lead before proceeding.

## Why "local staging" exists

The hub has three deployment environments:

| Env | Lives | Cloudflare tunnel | Daphne / dev-server | Code source |
|-----|-------|-------------------|---------------------|-------------|
| `dev` | developer workstation | none | Django dev-server (auto-reload) | bind-mounted host repo |
| `staging` | dev workstation OR NAS | none (direct access) | Daphne ASGI | copied into image |
| `prod` | NAS only | Cloudflare tunnel | Daphne ASGI | copied into image |

Local **staging** sits between `dev` (fast, mounted, debug-friendly)
and NAS-`prod` (real, locked down). It is the right surface for:

- Verifying a build is production-shape before pushing the NAS.
- Hand-testing flows that need a real ASGI server (websockets, daphne
  routing) — `dev` uses Django's dev server which behaves differently.
- Letting an Orochi agent drive the webapp end-to-end against a
  not-prod target.

## Pre-flight (no infra mutation)

Verify the workstation has what staging needs **without** running anything:

1. **Docker engine + compose v2**

   ```bash
   docker version            # engine running?
   docker compose version    # plugin v2 present?
   ```

2. **Repo + secrets**

   ```bash
   ls SECRETS/.env.staging   # required; not in git
   ls deployment/docker/envs/.env.staging    # may be a symlink to SECRETS/
   ```

   If `SECRETS/.env.staging` is missing, copy from `deployment/envs/`
   templates and fill in. **STOP** — request the staging secrets from
   the project lead; do not invent values.

3. **Free ports**

   Staging defaults (overridable via env):

   | Port | Service | Env var |
   |------|---------|---------|
   | `31294` | Django HTTP (daphne) | `SCITEX_HUB_HTTP_PORT` |
   | `2213`  | SSH (workspace) | `SCITEX_HUB_SSH_PORT` |

   ```bash
   ss -ltn | grep -E '31294|2213' || echo "ports free"
   ```

   If either is taken, override on the command line — do **not** edit
   the compose file.

4. **No `dev` or `prod` already running**

   The Makefile enforces mutual exclusivity, but it doesn't hurt to
   confirm:

   ```bash
   make status
   ```

5. **Branch + tree clean**

   ```bash
   git -C . status -s -b
   ```

   If you have uncommitted changes, decide whether they belong in the
   staging image or not — the prod-shape Dockerfile copies the repo
   tree into the image at build time.

## Launch (one operator command, several minutes)

> **STOP** — the project lead must explicitly approve before you run
> any of these on a fresh workstation. They allocate ports, start
> persistent services, and touch the local Docker daemon.

```bash
make ENV=staging start
```

This invokes `docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d`
under the hood. Services that come up (see `deployment/docker/docker-compose.yml` + `.staging.yml`):

- `postgres` (15-alpine) + `pgbouncer` — local DB, no host port exposed by default
- `redis` — local cache
- `django` (daphne ASGI, port `31294 → container 8000`)
- `gitea` — self-hosted Git
- supporting workers (Celery, channels) per the staging compose file

The Django service is built from `deployment/docker/Dockerfile.prod` —
this **rebuilds** if the image isn't cached. First-time launch on a
fresh workstation is typically 5–10 minutes.

## Trying the webapp — port-forward / direct access

Staging is the **direct-access** environment (no Cloudflare tunnel) so
the simplest path is just:

```
http://localhost:31294/
```

If you are on a remote workstation (e.g. SSH'd into a build box) and
want to drive the browser from your laptop, port-forward over SSH:

```bash
# from your laptop
ssh -L 31294:localhost:31294 your-workstation-host
# then visit http://localhost:31294/ in your laptop browser
```

`http://localhost:31294/health/` is the liveness probe used by the
container healthcheck — that's a good first URL to hit to confirm the
stack reached the ready state.

## Verifying functionality

Once the page loads, the smoke checks in priority order:

1. `/health/` returns `{"status": "ok"}` or similar — confirms ASGI + DB + Redis are wired.
2. `/admin/` reachable, login works (use the `test-user` / staging
   superuser per `SECRETS/.env.staging`).
3. `/api/v1/...` endpoint returns non-empty JSON for a known-good
   project ID (or `404` for a bogus one — both are "Django is alive").
4. `make logs-web` shows no exception traceback over a 60-second
   window.

Document anything unexpected in `docs/incidents/` rather than fixing
it in-flight from the runbook.

## Optional — wiring an Orochi orchestrator alongside

`scitex-orochi` is the multi-agent orchestrator that drives SciTeX Hub
from outside. Running it against your local staging is the same as
running it against any HTTP target, with one caveat: Orochi's master
agent expects to dial websockets at `ws://<host>:<port>/ws/`.

Workflow (descriptive — adjust paths to your checkout):

1. Confirm the local staging is up: `curl -sS http://localhost:31294/health/`.
2. In a separate clone of `scitex-orochi`, point its config at the
   local target (see `~/proj/scitex-orochi/orochi-config.yaml`):

   ```yaml
   orochi:
     server:
       host: 127.0.0.1
       ws_port: 31294
       dashboard_port: 31294
   ```

3. Launch the master with `scitex-orochi launch master`. The agent
   should print `connected to ws://127.0.0.1:31294/ws/...`.
4. From the master, send a test directive and watch the staging
   Django logs (`make logs-web`) for the corresponding request.

> **STOP** if Orochi requires anything other than read-only auth on
> the hub — do not give a local orchestrator production credentials.

## Teardown

Cleanly stop the environment (preserves volumes, so a re-launch is
fast):

```bash
make ENV=staging stop
```

Wipe volumes (irreversible — drops the local staging DB content):

```bash
make ENV=staging down       # stops + removes containers, keeps named volumes
docker volume ls | grep scitex-hub-staging   # find the leftovers
docker volume rm <volume-name>               # only if you are sure
```

**STOP** — do not run `docker volume rm` on anything that doesn't
match the staging name pattern. Production volumes share the Docker
daemon if the same workstation also has a prod sandbox.

## Known unknowns / discuss with lead

These are the things this runbook deliberately does **not** prescribe;
they need the project lead to decide:

1. **Staging secrets distribution.** Where does a new developer
   workstation obtain `SECRETS/.env.staging`? Currently undocumented
   here.
2. **Daphne port conflicts on shared dev boxes.** If two devs on the
   same workstation each want a staging, the `SCITEX_HUB_HTTP_PORT`
   env var needs a clear allocation rule (e.g. each developer picks
   `31294 + N` from an org-wide table).
3. **SLURM / Singularity bind mounts.** The staging compose file
   bind-mounts the SLURM controller config and `/etc/munge` from the
   host (read-only). On a workstation without SLURM these are missing
   files; behaviour is undefined. Either patch the compose with a
   `SCITEX_SLURM_PRESENT` flag or document the workaround here.
4. **`scitex-container` host path.** The compose bind-mounts
   `/home/ywatanabe/proj/scitex-container/src/scitex_container` as
   read-only into the Django container — that's a developer-specific
   path. Locally-staged workstations of other users need either the
   same path or an env override.
5. **Orochi `dashboard_port`.** Orochi's config currently treats the
   websocket port and dashboard port as the same value; staging serves
   both from one daphne instance, but that should be confirmed before
   we depend on it.

## Recovery checklist (if something goes wrong)

| Symptom | Most-likely cause | First check |
|---------|-------------------|-------------|
| `make ENV=staging start` exits non-zero | Port collision OR missing `.env.staging` | `ss -ltn` and `ls SECRETS/.env.staging` |
| Containers up but `/health/` is 502 | Daphne crashed during boot | `make logs-web` for traceback |
| `/admin/` shows `OperationalError` | DB not yet migrated | `make migrate ENV=staging` |
| `make logs-web` shows `ImportError: scitex.cloud` | Stale image after rename | `make ENV=staging rebuild` |

Once recovered, capture what happened in `docs/incidents/` with a
date-stamped filename — the next person who hits this will thank you.

## See also

- `deployment/README.md` — top-level deployment topology (dev / staging / prod).
- `docs/DEV_VS_NAS.md` — when to deploy to NAS vs run locally.
- `docs/incidents/` — past failures and what fixed them.
- `~/proj/scitex-orochi/docs/getting-started.md` — orochi-side launch.

<!-- EOF -->
