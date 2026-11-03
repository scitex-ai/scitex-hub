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

The earlier install layers are cache inputs, not independent dependency
solutions. After their final install, `installed_runtime_roots.py` records every
retained distribution name. One normal `uv pip install` resolves those names
together with the local Hub's `[all]` extra, followed by `uv pip check`. This
preserves cached packages while repairing incompatible dependencies left by
separate install transactions. No dependencies or failed checks are omitted.
The frontend is baked only after this resolution, so its recorded Python graph
is the graph actually shipped. The final relationship verifier still runs
after all installs and frontend preparation.

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
Development uses `docker_dev/install_ecosystem.sh` and direct sibling binds;
that layout is **not** the apps-volume model. Automatic `--env dev` therefore
refuses that unmodelled overlay instead of probing an invented volume. Changing
its environment value to `image-only` cannot make the direct development
installer implement that mode.

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
