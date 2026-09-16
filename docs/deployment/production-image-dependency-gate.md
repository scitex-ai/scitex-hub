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
