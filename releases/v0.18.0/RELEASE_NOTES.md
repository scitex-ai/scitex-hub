# v0.18.0 - 2026-05-23

## Renamed: `scitex-cloud` → `scitex-hub` (BREAKING)

This release renames the project end-to-end. The "cloud" name implied a
vendor-hosted service, but in reality this is a **self-hostable
research hub** — laptop, lab server, NAS, or cloud — so the name now
matches the product.

See [ADR-0001](../../docs/adr/0001-rename-scitex-cloud-to-scitex-hub.md)
for the full rationale and migration policy.

### Scope of the rename

| Layer | Before | After |
|---|---|---|
| PyPI distribution | `scitex-cloud` | `scitex-hub` |
| Python module | `import scitex_cloud` | `import scitex_hub` |
| GitHub repo | `ywatanabe1989/scitex-cloud` | `ywatanabe1989/scitex-hub` |
| Display / brand | "SciTeX Cloud" | "SciTeX Hub" |
| Django sub-app | `apps/workspace/hub_app/` | `apps/workspace/repo_app/` |
| Runtime env vars | `SCITEX_CLOUD_*` | `SCITEX_HUB_*` |
| Campaign tokens | `scitex-cloud-campaign-*` | `scitex-hub-campaign-*` (legacy alias accepted) |
| Container image | `scitex-cloud-shared-v0.1.0.sif` | `scitex-hub-shared-v0.1.0.sif` |
| Docker compose containers | `scitex-cloud-{env}-{svc}-1` | `scitex-hub-{env}-{svc}-1` |

### Why now

Eight prior releases (through v0.17.6) shipped under `scitex-cloud`.
The project is still alpha and there is no installed-base cost large
enough to justify dragging the wrong name forward. The longer we wait
the higher that cost grows. Now is the cheapest point to cut over.

### Migration

#### Python callers
```diff
- import scitex_cloud
+ import scitex_hub
```
There is **no compat alias module** — `import scitex_cloud` raises
`ImportError` with a pointer to this release.

#### PyPI installers
```diff
- pip install scitex-cloud[mcp]
+ pip install scitex-hub[mcp]
```
The old `scitex-cloud` PyPI distribution is published one last time as
a stub that raises `ImportError` at import-time, with a link back here.

#### Deployments (`.env`)
Rename every variable prefix in your `.env` / `.env.dev` / `.env.prod`:
```diff
- SCITEX_CLOUD_DJANGO_SECRET_KEY=...
- SCITEX_CLOUD_POSTGRES_DB=...
- SCITEX_CLOUD_GITEA_TOKEN=...
+ SCITEX_HUB_DJANGO_SECRET_KEY=...
+ SCITEX_HUB_POSTGRES_DB=...
+ SCITEX_HUB_GITEA_TOKEN=...
```
A one-liner if you trust your `.env` content:
```bash
sed -i 's/SCITEX_CLOUD_/SCITEX_HUB_/g' deployment/docker/envs/.env.{dev,prod,staging}
```
Then `make ENV=dev restart` (etc.).

#### Postgres database name
Default DB names changed from `scitex_cloud_{env}` to `scitex_hub_{env}`.
Existing databases continue to work if you explicitly set
`SCITEX_HUB_POSTGRES_DB=scitex_cloud_{env}` in your env. New installs
get the new default.

#### Docker container hostnames
If you bind to the legacy `scitex-cloud-dev-django-1` hostname from
outside compose (e.g. host-side scripts), update to
`scitex-hub-dev-django-1`. Compose-internal service names are
unchanged.

#### Campaign tokens
Existing `scitex-cloud-campaign-YYYYMMDD-YYYYMMDD-hashtag` tokens
**continue to work** as a back-compat alias. The parser emits a
`DeprecationWarning` on every legacy hit so you can find them in logs.
Re-issue tokens with the `scitex-hub-campaign-` prefix at your
convenience; the legacy alias will be removed in a future major
release.

#### GitHub URLs
GitHub's repo-rename redirect handles `git clone`,
`pip install git+https://github.com/ywatanabe1989/scitex-cloud`, and
issue/PR links for a grace period. We rely on that — no mirror.
Update your local remote:
```bash
git remote set-url origin https://github.com/ywatanabe1989/scitex-hub.git
```

#### Local working tree
If you keep the source at `~/proj/scitex-cloud`, rename it once:
```bash
mv ~/proj/scitex-cloud ~/proj/scitex-hub
# update any symlinks under ~/.config/ or your editor workspace
```
A symlink `~/proj/scitex-hub -> ~/proj/scitex-cloud` keeps things
working in the interim.

### Snapshot tag

The pre-rename HEAD is preserved at tag `pre-rename-cloud-to-hub`
(commit `379018c4`). The whole rename was executed with
`scitex-dev rename-symbols`, which is reverse-rename-safe — re-running
each step with old/new swapped restores the previous state.

### What is *not* renamed (intentionally)

- `CHANGELOG.md` entries for v0.17.6 and earlier — they describe
  releases that shipped under the historical "SciTeX Cloud" name and
  are preserved verbatim.
- `deployment/.archive/` — archived legacy configs (uwsgi, manual
  nginx, ...).
- Cloudflare-related templates and scripts (`cloudflare-tunnel-status.html`,
  `cloudflare_cache_purge.sh`) — Cloudflare is an external CDN service
  name, not our brand.
- The `_sphinx_html/` generated docs were rebuilt under the new module
  name; pre-existing artefacts referencing the old name are overwritten
  by CI on the next docs build.

## Upgrade summary

For a fresh install or one-time migration:

```bash
# 1. Update Python deps
pip uninstall -y scitex-cloud
pip install scitex-hub[mcp]

# 2. Update the source tree + remote
cd ~/proj/scitex-cloud && git pull && git remote set-url origin \
  https://github.com/ywatanabe1989/scitex-hub.git
cd .. && mv scitex-cloud scitex-hub

# 3. Update deployment env vars
sed -i 's/SCITEX_CLOUD_/SCITEX_HUB_/g' \
  ~/proj/scitex-hub/deployment/docker/envs/.env.*

# 4. Restart
cd ~/proj/scitex-hub && make ENV=dev restart
```

If anything goes wrong, the snapshot tag `pre-rename-cloud-to-hub`
restores the pre-rename state on the source side, and `pip install
scitex-cloud` restores the pre-rename PyPI package.
