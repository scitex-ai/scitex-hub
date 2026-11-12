# Production deployment

Follow the [canonical image deployment runbook](../../../src/scitex_hub/_skills/scitex-hub/12_deployment-production.md).
It covers private candidate builds, real resource bounds, immutable image
qualification, staging, backups, targeted app-role deployment and rollback.

## Build prerequisites

The production Dockerfile expects a verified host-provided `yq` binary in its
build context. A fresh worktree does not contain that ignored file. Use the
runbook's **Prepare the production build context** instructions before building.
Building an image and qualifying a running service are separate steps.

## Inspect the current stack

From the selected repository root:

```bash
scripts/deploy/compose.sh prod ps
scripts/deploy/compose.sh prod logs --tail=100 django
```

The wrapper selects the canonical Compose files and private environment file.
Keep environment values and service logs private. Use the runbook's checked
procedure for changes to running services.

## Configuration authorities

- [Production Compose](docker-compose.yml) declares the stack.
- [Compose environment resolver](../../../scripts/deploy/compose_env.sh) selects environment files, overlays and image modes.
- [Canonical Compose wrapper](../../../scripts/deploy/compose.sh) applies that resolved configuration and the deployment preflight.

Preserve existing data, configuration, unrelated services and active jobs.
Beta launch remains subject to the operator's explicit approval.
