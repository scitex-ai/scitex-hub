---
description: |
  [TOPIC] Deploy to Production
  [DETAILS] Build a bounded candidate, qualify one immutable staging artifact, and deploy targeted app roles while preserving rollback state.
tags: [scitex-hub-deployment-production]
---

# Deploy one qualified image to staging and production

The source authorities are `scripts/deploy/compose_env.sh`,
`deployment/docker/docker_prod/docker-compose.yml`,
`deployment/docker/docker-compose.staging.yml` and the sibling/image dependency
checks. Use the canonical wrapper; never substitute a bare Compose invocation
that omits its reviewed env-file and overlays. Keep resolved environment JSON
and credentials private. Existing authorization governs the deployment scope.

## Preserve serving state before building

Record the accepted source, all running image/container identities, process
births and persisted mounts. Preserve the current writable-layer repairs as
private rollback images when present; an old image tag cannot capture them.
Take a consistent database dump, restore it into an owned isolated database,
and preserve user/media/static/config/frontend mount data where startup writes.
A live file archive is not a quiescent cross-resource snapshot. Retain the old
hashed static chunks. Never publish private rollback images or database dumps.

Preserve existing user-data and configuration ownership and file modes through
startup. Private `0700` directories and `0600` files are valid, not broken
permissions. Qualify an owned private fixture before and after boot. Inaccessible
existing data requires a separately reviewed operator repair; do not recursively
change its ownership or widen its permissions to make startup succeed. Only
absent directories or empty root-owned mount roots may be initialized for the
application user with private permissions.
The Docker constructor separately prepares all ten image-owned state directories
and existing image configuration after the final install/import gates. It must
precreate `/app/data` before nested users mounts can be attached. Build-time
`scripts/deploy/verify_default_bootstrap.py` gates inspect those defaults and run
the complete root initializer with empty synthetic private tmpfs mounts under
`--network=none`. This initialization concerns image defaults only; do not
recursively repair runtime mounts. Require the canonical image cold boot and
actual staging/native smoke before tagging or publishing the successor.
See [the bootstrap permission boundary](../../../../docs/security/container-data-permissions.md)
for the source-backed checks and root-owned mount qualification.

`rebuild.sh` is NOT the preserve-jobs route: it cancels SLURM jobs after building
and then swaps services. It has no build-only option. Its current build command
uses `nice`, but does not create a systemd build scope or take the stack down
before building. `make build` has no swap, but does not enforce worker limits.
Do not stop unrelated services or delete Redis, jobs or mounted data to deploy.
Development app startup must not cancel jobs or reset scheduler node states.
Keep scheduler recovery separate from web and worker starts.

## Build a candidate without changing production's latest tag

Prepare a task-private `DOCKER_CONFIG` and an owned named `docker-container`
Buildx worker, leaving existing builders and credentials untouched. Verify its
actual kernel CPU/memory caps and configured `max-parallelism`; lowering the
Docker CLI's priority does not limit daemon-side build workers. For example,
a reviewed worker can have a two-CPU quota, 12 GiB memory/swap total and two
parallel operations. These are bounds, not a hardware or completion guarantee.
Check the installed Compose/Buildx versions before choosing driver options;
Compose 2.26.1 embeds Buildx 0.13.1 and does not understand `default-load`, while
its single-platform build already requests Docker image loading.

From the accepted repository, with `DOCKER_CONFIG` and `builder_name` set to
that prepared task-private worker:

```bash
: "${DOCKER_CONFIG:?set the prepared private Docker configuration}"
: "${builder_name:?set the reviewed owned Buildx worker name}"
export SCITEX_HUB_APP_IMAGE="scitex-hub-candidate:alpha-$(git rev-parse --short=12 HEAD)-$(date -u +%Y%m%dT%H%M%SZ)"
export SCITEX_HUB_DEPENDENCY_RESOLUTION="$(scripts/deploy/resolve_dependency_resolution.sh prod)"
DOCKER_BUILDKIT=1 nice -n 10 ionice -c 2 -n 7 \
  scripts/deploy/compose.sh prod build --builder "$builder_name" django
release_image="$(docker image inspect "$SCITEX_HUB_APP_IMAGE" --format '{{.Id}}')"
```

`SCITEX_HUB_APP_IMAGE` selects the same image for Django, worker and beat.
Unset defaults remain the existing environment-specific `:latest` references;
use a unique tag for building, then an immutable identity for admission/swap.
The canonical resolver rejects empty/malformed overrides without printing the
value. Resolver-owned image/mode values prevent dotenv files from silently
selecting an unvalidated candidate. With a candidate override, staging is derived as `image-only` for all
three roles with baked frontend publication; ordinary staging remains editable
with runtime frontend build mode. Both modes are derived by the canonical
resolver, not caller overrides. Production is always image-only/baked.
An ambient mode variable cannot change this policy. Development's direct-bind
installer does not support this image override.
Development installs the full npm graph after source peers are mounted; an
existing `node_modules` directory is not dependency evidence. A failed install
or bundle build stops startup, even if an earlier manifest remains. `SCITEX_UI_SOURCE_DIR` can select the release-matched legacy npm
provider when the default sibling is absent; retain the SDK as the shared GUI
owner and qualify the actual editable peer graph before recreation.

## Qualify once, stage the same artifact

Use the resulting full `sha256:` local image ID on the same Docker engine, or
a verified repository `@sha256:` digest when transferring through a registry.
Do not rebuild or re-resolve dependencies between staging and production.

```bash
: "${release_image:?set the qualified immutable image identity}"
export SCITEX_HUB_APP_IMAGE="$release_image"
scripts/deploy/preflight_sibling_floors.sh prod --json
```

Also qualify the image's real installed dependency graph, import contract,
namespace/static manifests and migration behavior against an isolated restored
database. Image-only disables editable Python replacement and does not suppress
mandatory migrations. Production images explicitly select `SCITEX_HUB_FRONTEND_MODE=baked`:
their verified frontend artifact is built into the same image, and startup does
not clone repositories or run npm/Vite. Legacy `build` mode retains runtime
frontend preparation; it is not the production artifact qualification path. See
[the baked frontend contract](../../../../docs/deployment/baked-frontends.md).
The source verifier is
`scripts/deploy/verify_image_dependency_contract.py`. Source/runtime/fixture
proof is not permission to use an unqualified image or waive a failing floor.

For staging, use an explicitly owned test-user root, never the production users
bind. Prepare fixtures there and check actual resolved mounts before recreation:

```bash
: "${stage_users:?set an owned isolated staging user directory}"
export SCITEX_SLURM_USER_DATA_ROOT="$stage_users"
scripts/deploy/preflight_sibling_floors.sh staging --json
scripts/deploy/compose.sh staging up -d --no-deps --no-build --wait --wait-timeout 900 django
scripts/deploy/compose.sh staging up -d --no-deps --no-build --wait --wait-timeout 900 celery_worker celery_beat
```

Staging uses its own env-file, database and named volumes. Verify those identities
and the selected users bind; a different app name alone is not isolation.

Set `DEBUG=False` in the canonical staging env-file: image-only/baked Django
must serve the verified manifest rather than request a Vite development server.
The preflight refuses that debug-mode mismatch before recreation. An exported
shell variable does not replace a value supplied through Compose's env-file.

Check real authorized routes, frontend hashes, worker/beat behavior and relevant tests.
A web-first start completes migrations before the worker and scheduler start.
The readiness grace covers measured cold static publication; it does not replace
the authenticated page and asset checks.
A healthy container or HTTP 200 by itself is insufficient evidence. Audit root
and linked frontend dependency locks separately, and qualify actual diagram
rendering boundaries; see [diagram rendering](../../../../docs/security/diagram-rendering.md).
Do not equate a successful build or root-only npm audit with a clean security graph.
Also verify the actual public `/sw.js` bytes against the accepted source; its
collected copy is served separately from the Vite manifest. Check private-cache
isolation with service workers enabled, as described in
[the service-worker boundary](../../../../docs/security/service-worker-cache.md).

## Apply only the qualified production change

After source/cohort, staging, backup freshness and migration/rollback gates pass,
clear the staging-only users override and recheck production mount identities:

```bash
unset SCITEX_SLURM_USER_DATA_ROOT
scripts/deploy/preflight_sibling_floors.sh prod --json
scripts/deploy/compose.sh prod up -d --no-deps --no-build --wait --wait-timeout 900 django
scripts/deploy/compose.sh prod up -d --no-deps --no-build --wait --wait-timeout 900 celery_worker celery_beat
```

If production has a reviewed nondefault users root, restore that exact value
instead of unsetting it. Preserve existing named, bind and anonymous volumes;
do not request volume renewal, broad `down`, orphan removal or job cancellation.
Database, Redis, Gitea, nginx and tunnel services stay outside this targeted swap.
Recheck current jobs and any admission constraints at the actual swap time.
Read bounded sanitized logs and exercise real routes/static assets after boot.
Image-only startup still performs mandatory dependency and migration checks.

## Rollback is a separate qualified state

Preserve the exact old source/config, per-role private snapshots and mounted data.
Historical roles may have different image IDs and package graphs; they are not a
new same-image candidate, and do not establish compliance with the new contract.
Rehearse their reviewed restoration procedure separately. A successful logical
DB restore is useful evidence but not a complete application rollback rehearsal.
Image rollback does not reverse schema/data migrations or restore overwritten
static files. No floor waiver or skip-gate flag is provided by this runbook.
