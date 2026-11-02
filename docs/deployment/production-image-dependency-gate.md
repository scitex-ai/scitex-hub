# Production image dependency-floor gate

The production runtime uses the Python dependency graph baked into
`Dockerfile.prod`. `SCITEX_APPS_PYTHON_MODE=image-only` still permits sibling
clones for Vite bridge discovery, but forbids `pip install -e` from replacing
that validated graph at container start. All Hub Python services declare the
same mode.

The final Docker stage runs `scripts/deploy/verify_image_dependency_contract.py`
after all installs. It checks Hub's declared sibling floors, every installed
sibling's active `Requires-Dist` relationships, and the explicit import/attribute
contracts in `preflight_contract.json`.

## Non-production canary and rollback evidence

Use the existing `nightly-staging-candidate-YYYYMMDD` GHCR artifact as the
noncritical canary; do not retag `latest` or alter production compose links.
Record the pushed `ghcr.io/scitex-ai/scitex-hub@sha256:...` digest. Before a
manual staging run, record the currently configured staging digest as the
rollback artifact (`staging-pre-dependency-floor-gate@sha256:...`). A valid
release record contains both immutable digests and verifier output from the
candidate. A local image ID or mutable tag is not immutable evidence.

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

Staging declares its existing `editable` startup mode explicitly. That legacy
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
