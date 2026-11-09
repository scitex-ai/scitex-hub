# Production image dependency-floor gate

The production runtime uses the Python dependency graph baked into
`Dockerfile.prod`. `SCITEX_APPS_PYTHON_MODE=image-only` forbids `pip install -e`
from replacing that graph at container start. All Hub Python services declare
the same mode. Production also selects `SCITEX_HUB_FRONTEND_MODE=baked`, which
verifies the image's complete frontend artifact and copies it after normal
collectstatic, without startup Git/npm. See [baked frontends](baked-frontends.md).

The final Docker stage runs `scripts/deploy/verify_image_dependency_contract.py`
after all installs. It checks Hub's declared sibling floors, every installed
sibling's active `Requires-Dist` relationships, and the explicit import/attribute
contracts in `preflight_contract.json`.

The earlier anchor, C0 and C1 installs are cache inputs, not independent final
solutions or final version floors. After their last install,
`installed_runtime_roots.py` derives a capability root set from installed
metadata: every SciTeX distribution (including FigRecipe), each currently
installed dependency directly declared by those owners, and the explicit
Docker runtime capability names and Python packaging tools. For example, the
old Daphne cache pin does not override Hub's newer declared Daphne floor. Declared optional extras
contribute an already-installed direct dependency when its platform marker
applies. Missing optional packages are not invented. The local Hub is admitted
through its actual `[all]` source input, not an index substitute.

The helper seeds the output lock with validated cached versions. These are
`uv pip compile` preferences, not a constraints file: normal resolution can
change a cached version to satisfy the complete graph. Do not add `--upgrade`
(which discards those preferences). Compilation must succeed before `uv pip
sync` installs exactly that resolved closure. Sync can remove a helper needed
only by a superseded third-party version; retaining every cached transitive
name would incorrectly make those obsolete helpers permanent requirements.
There is no package-specific orphan allowlist, dependency override, or
`--no-deps` install. A genuinely incompatible retained owner still fails
resolution. The image retains `runtime-roots.manifest.json` with the complete baseline
names/versions/requirements, per-root reasons and cached preference inputs;
`runtime.cached-preferences.in` preserves the original seed separately from
the compiled `runtime.lock`. After sync, `--verify-closure` refuses missing
retained capabilities and records final versions, removals and lock digest.
`uv pip check` and the late image verifier remain mandatory.

The frontend is baked only after this complete resolution, so its recorded
Python graph is the graph actually shipped. The final relationship verifier
still runs after all installs and frontend preparation. This policy preserves
installed capabilities; it does not claim every optional extra is active or
that the old cached versions remain the final supported versions.

## Non-production canary and rollback evidence

Use a separately qualified candidate without retagging production's `latest`.
For a registry-backed canary, record its verified repository `@sha256:` digest
and the previous known-good digest. On one Docker engine, a full local image ID
binds the exact image content for admission and reuse, but does not prove a
registry publication or source qualification. Record source/payload provenance
and actual verifier output in either case; a mutable tag alone is insufficient.
Historical rollback images and mounted-data backups need separate restoration
qualification, especially when previous app roles had different package graphs.

## The pre-recreate sibling check uses the same runtime mode

`scripts/deploy/compose.sh prod up ...` calls the sibling floor/import gate.
With `--env`, that gate sources the **same** `compose_env.sh` mapping and runs
its exact env-file/overlay Compose command with `config --format json`. It
parses the result in memory. Resolved environments, interpolation values and
Compose stderr are never printed or written into a report because they can
contain credentials.

Django, worker and beat must explicitly agree on `SCITEX_APPS_PYTHON_MODE` and
image. Missing, mixed or unsupported declarations refuse the check before the
target is interrogated. An unreadable Compose configuration is not a pass.

In `image-only`, the gate interrogates the declared image without an apps-volume
mount, clone-version override or clone `sys.path` insertion. The `/app/.apps`
volume may still exist for frontend discovery; that does not make it a Python
package source. An explicit `--apps-volume` conflicts with this mode and is
refused. A clone path in image-only `PYTHONPATH` is refused too. Floors and real
imports remain mandatory; a correct mode never turns a failing floor green.

Ordinary staging declares its existing `editable`/`build` modes explicitly;
candidate-image staging selects `image-only`/`baked`. The legacy editable
mode derives the actual apps mount from resolved Compose volume names and
requires all three Python roles to agree. It does not guess a volume from an
environment-name suffix. A different explicit volume is not the same deployment.
Development uses `docker_dev/install_ecosystem.sh` and direct sibling binds,
which have a separate `direct-bind` preflight. On the Docker host, automatic
`--env dev` recognizes the canonical development project and entrypoint, then
requires all three Python roles to agree on the image and package-source binds.
It reads the installer's package and extras declarations, including the full
Hub and umbrella `[all]` requests. It does not invent an apps volume or accept a
bare image/current-container diagnostic as a replacement for that profile.

The implementation in `scripts/deploy/_direct_bind/` snapshots the declared Git
sources into an owned private workspace. Source edits must be committed first;
the supported exception is a bounded, regular `package-lock.json` beside a
tracked `package.json`. Those generated locks are fingerprinted and copied,
not discarded. The original checkouts remain untouched. The preflight runs the
canonical simultaneous editable install and `uv pip check` in a separate
container with two CPUs and 8 GiB memory/swap, using the resolved image ID.
It then disconnects that owned container's network, probes its actual installed
graph and imports, and checks source identity again before cleanup. No serving
user/database mounts enter this preparation container. The install needs
dependency-index access; the import probe runs without a network.

Run this check on the development Docker host:

```bash
scripts/deploy/preflight_sibling_floors.sh dev --json
```

An unmodelled overlay, mixed source declarations, changed/unreadable source,
failed installation, failed dependency check or failed import still refuses
the recreate. `--via-ssh` does not model remote direct binds: SSH to the Docker
host and run its canonical wrapper there. Changing the development mode to
`image-only` does not make its installer implement that mode. Source-level
controls for this path are in `tests/deployment/test_preflight_direct_bind.py`
and `test_preflight_lock_snapshots.py`; passing them alone does not qualify a
particular host's prospective package graph or frontend.

For a recreate, `compose.sh <env> up ...` keeps the sanctioned mapping.
Configuration-changing global options before `up` (for example a different
`-f`, `--env-file` or project name) are refused because the gate cannot
truthfully model a different invocation. Declare a reviewed overlay in
`compose_env.sh` so both config resolution and recreate share it. Ordinary
`compose.sh prod build ...`, `prod up ...` and non-recreate commands remain
supported. There is no bypass flag.

An explicit `--target` remains explicit: its image/container/local/custom runner
identity is never replaced, and no implicit apps overlay is attached to it.
Without `--env`, existing standalone target diagnostics keep their existing
behavior. With `--env`, the declared mode is still validated, and an explicitly
requested editable overlay must match Compose. A container/local diagnostic
is not evidence for the image used by a future recreate. Over SSH, automatic
Compose resolution requires `--repo-root` to exist at the same path on the
Docker host; otherwise the check refuses without guessing a remote checkout.

This gate checks the Python floor/import contract. It does not replace the
immutable image verifier, migration planning, data backups, frontend/static
qualification or the guarded production swap and rollback procedure.
The import probe configures Django with no apps or database. Non-import
exceptions are reported as `INCONCLUSIVE`, not successful imports, and do not
by themselves fail this dependency gate. Verify those modules under the real
host configuration and relevant application tests before claiming readiness.

## Candidate image selection

`SCITEX_HUB_APP_IMAGE` is the shared optional image identity for the three
production and three staging app-service image fields. The canonical resolver
validates it before invoking Compose and exports resolver-owned image/mode values;
values in dotenv files cannot silently select a different candidate; an explicitly empty/unsafe value refuses
without echoing it. Unset image defaults are unchanged. Candidate tags are for
building; deployment admission uses the resulting immutable image ID or verified
registry digest. Production stays image-only, while a candidate override derives
image-only for all staging roles regardless of ambient mode values. Ordinary
staging remains editable. Development's direct-bind installer rejects this
override rather than silently ignoring it.

Build through `scripts/deploy/compose.sh prod build --builder <owned-name> django`
with a resource-qualified private Buildx worker and a unique candidate tag. Stage
the same artifact using `--no-build`, separate staging data and an owned
`SCITEX_SLURM_USER_DATA_ROOT`. Follow the source-owned
[deployment runbook](../../src/scitex_hub/_skills/scitex-hub/12_deployment-production.md)
for admission, targeted recreation and rollback limitations. This setting does
not authorize a deployment or turn the generic job-cancelling rebuild into a
safe preserve-jobs workflow.
