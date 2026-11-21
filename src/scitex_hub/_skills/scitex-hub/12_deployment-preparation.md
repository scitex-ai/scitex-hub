---
description: |
  [TOPIC] Prepare deployment state and build context
  [DETAILS] Preserve private rollback data, SSH identity and scheduler state; prepare the verified production yq asset before building a candidate.
tags: [scitex-hub-deployment-preparation]
---

# Prepare deployment state and build context

Complete these steps before the [candidate build and rollout](12_deployment-production.md).
Existing authorization governs the environment and deployment scope.

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
Before recreating a gateway-serving app, complete the
[SSH identity handoff](../../../../docs/security/container-data-permissions.md#ssh-gateway-identity).
Verify the running gateway's wire fingerprint and preserve its private key in
the selected persistent directory. An empty new directory does not authorize
a new server identity. Keep the legacy key and private rollback state.
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

## Prepare the production build context

`deployment/docker/docker_prod/Dockerfile.prod` copies a host-provided AMD64
`yq` binary from `deployment/docker/docker_prod/bin/yq_linux_amd64`. That ignored
asset is absent from a fresh Git worktree. Prepare it before the candidate
build; the Dockerfile does not download it. Use the official v4.47.1 asset and
verify its SHA256 before admitting it to the build context:

```bash
(
  set -eu
  asset=deployment/docker/docker_prod/bin/yq_linux_amd64
  mkdir -p "$(dirname "$asset")"
  prepared="$(mktemp "${asset}.download.XXXXXX")"
  trap 'rm -f "$prepared"' EXIT
  curl --fail --location \
    https://github.com/mikefarah/yq/releases/download/v4.47.1/yq_linux_amd64 \
    --output "$prepared"
  printf '%s  %s\n' \
    0fb28c6680193c41b364193d0c0fc4a03177aecde51cfc04d506b1517158c2fb \
    "$prepared" | sha256sum --check -
  chmod 755 "$prepared"
  mv "$prepared" "$asset"
)
```

Run this from the selected worktree root. This prepares a public build tool;
it does not prepare a candidate image or authorize a service recreation.
The SHA256 matches the upstream release asset digest. Preserve any failed
build's logs and record changed context inputs before starting another build.

