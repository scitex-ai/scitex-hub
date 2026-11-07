---
description: |
  [TOPIC] Deploy to Staging
  [DETAILS] Stage the qualified immutable app image with isolated user data through the canonical deployment contract.
tags: [scitex-hub-deployment-staging]
---

# Stage the qualified production artifact

Follow [the canonical image deployment runbook](12_deployment-production.md),
particularly **Qualify once, stage the same artifact**. It owns the shared
build, resource limits, backups, image admission and verification sequence.

Staging is selected through `scripts/deploy/compose.sh staging ...`; the shared
resolver supplies `deployment/docker/envs/.env.staging` and the base/staging
Compose files. Its build points to the production Dockerfile (the compatibility
path `deployment/docker/Dockerfile.prod` resolves to
`deployment/docker/docker_prod/Dockerfile.prod`). For release qualification,
build once through the production candidate path and stage that exact immutable
artifact with `--no-build`; do not independently rebuild a different graph.

A supplied `SCITEX_HUB_APP_IMAGE` selects all three app roles and derives
image-only mode. Without it, staging keeps its historical editable default.
Use the existing `SCITEX_SLURM_USER_DATA_ROOT` bind parameter for an explicitly
owned isolated test-user directory; verify the database, volumes and actual
resolved mounts before a staged swap. Never run the generic job-cancelling
`rebuild.sh`, broad `down`, or unconditional no-cache build as a staging recipe.
Ports and route readiness come from the resolved reviewed configuration rather
than stale hardcoded port numbers. Preserve production and unrelated services.
