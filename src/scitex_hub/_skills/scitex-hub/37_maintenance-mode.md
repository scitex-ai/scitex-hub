---
description: Close new Hub requests with a local operator flag while distinguishing admission control from job draining and storage safety.
---

# Maintenance workflow

Establish which host and mounted filesystem the planned work affects before
changing admission. Inspect the running containers' mounts as well as the
host's mount table. A compose declaration or a successful HTTP response alone
does not establish where user data lives.

The maintenance gate closes new HTTP requests, including MCP and mounted
leaf APIs, and declines new WebSocket handshakes. It returns a self-contained
503 page or JSON error with `Retry-After` and `Cache-Control: no-store`.
It runs before session, authentication, and leaf handlers. Staff status,
request headers, and query parameters do not bypass it.

## Configure a trusted local state directory

The gate is disabled when `SCITEX_HUB_MAINTENANCE_FILE` is unset or the
configured file is missing. A malformed or unreadable file closes admission.
The state must be a regular file; symlinks and device/FIFO nodes are rejected.
Keep this state on storage that remains available during the outage, outside
user projects and tenant-controlled directories. Do not delete an enabled
flag to repair it: deletion reopens admission.

For container deployments, the optional
`deployment/docker/docker-compose.maintenance.yml` overlay adds a read-only
directory mount to the `django` service. Set `SCITEX_HUB_OPERATOR_STATE_DIR`
to an existing operator-owned local directory, and provide container-readable
ownership for that directory and its mode-0600 state file. The container UID
or a narrowly scoped ACL must be able to read it; do not make it writable by
web users. Mount the directory, because atomic replacement of a host file
does not update a container's bind of the old file inode.

Adding the gate to a deployed image or changing its mounts is an initial
deployment. Once installed, enabling and disabling maintenance requires no
Hub restart. This candidate does not activate maintenance in a running site.

## Close admission and account for writers

On the trusted operator host, use the configured host-side file path:

```bash
scitex-hub maintenance --state-file /opt/scitex/operator/maintenance.json enable --retry-after 300 --json
scitex-hub maintenance --state-file /opt/scitex/operator/maintenance.json status --json
```

Verify 503 responses for the workspace, a mounted leaf API, and `/mcp`,
and verify that a new WebSocket handshake is declined. The exact `/livez/`
endpoint stays 200 without touching the database, sessions, or user storage.
The probes and gate precede HTTPS redirect middleware, consistently with the
outer ASGI gate. When maintenance is disabled, normal workspace requests
retain the configured HTTPS redirects. The exact `/maintenance-ready/`
endpoint reports only admission state:
503 while closed and 200 while open. It is not a storage or database
readiness check. `/healthz/` still delegates to the existing health handler.

Closing admission does not cancel requests already in progress, established
WebSockets, Celery jobs, scheduled tasks, or external writers. This
implementation does not pause queues, drain jobs, verify mount identity, or
provide an edge fallback when the web process itself is unavailable. Inspect
and handle those writers separately before disconnecting storage that they
use. Do not describe a passing admission check as a drained or safe system.

## Restore admission

Confirm the intended storage has returned and its identity matches the
pre-outage observation. Verify the services and affected project paths before
reopening admission:

```bash
scitex-hub maintenance --state-file /opt/scitex/operator/maintenance.json disable --json
```

Verify a workspace and the affected leaf app. Report initial deployment,
flag state, mount checks, and job state separately.

## Validate without live infrastructure

Use a private environment and the isolated settings, which do not load
deployment dotenv files or configure a database:

```bash
PYTHONPATH="$PWD:$PWD/src" DJANGO_SETTINGS_MODULE=tests.platform.maintenance_settings \
  python -c 'import django, pytest; django.setup(); raise SystemExit(pytest.main(["tests/platform/test_maintenance_admission.py", "--confcutdir=tests/platform", "-q", "-p", "no:cacheprovider"]))'
```

The suite exercises changes observed by the same running client, protocol
admission, invalid state, message escaping, private atomic writes, and
preservation of the existing flag when replacement fails.
