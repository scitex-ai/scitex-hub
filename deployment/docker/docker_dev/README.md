# Development

## Start

```bash
make env=dev start
```

## URLs

| Service | URL |
|---------|-----|
| Django | http://localhost:8000 |
| Gitea | http://localhost:3001 |
| Flower | http://localhost:5555 |

## Test User

- Username: `test-user`
- Password: printed by `init_test_user` on first run (set `SCITEX_HUB_TEST_USER_PASSWORD` to choose it)

## Commands

```bash
make env=dev status
make env=dev logs
make env=dev restart
make env=dev rebuild
```

## Mounted package cohort

Development startup verifies the final Python dependency environment after all
editable installs. A later sibling can replace an earlier SDK during dependency
resolution; an incompatible result now stops startup instead of serving stale
capabilities. Update conflicting sibling requirements as one cohort rather than
forcing an incompatible package with `--no-deps`.

The Django, Celery worker and Celery beat services share the same development
mounts. Live Paper is mounted and installed with its server extra. Crossref and
OpenAlex clients use their core dependencies, without server/docs extras or local
corpus database mounts. For remote corpus services, configure their documented
HTTP modes and API URLs.

Use these optional Compose variables to select qualified standalone source
checkouts while preserving work in the usual sibling repositories:

- `SCITEX_DEV_SOURCE_DIR`
- `SCITEX_LIVE_PAPER_SOURCE_DIR`
- `CROSSREF_LOCAL_SOURCE_DIR`
- `OPENALEX_LOCAL_SOURCE_DIR`

Each defaults to its conventional sibling directory. A standalone clone keeps
its Git metadata available inside its mount; a linked worktree whose `.git` file
points outside the container may not support version generation. Recreate the
services after changing mount sources. Never replace an existing source tree to
change these overrides.

Terminal compute image and workspace paths must be configured for the compute
nodes. Sample `/path/to/...` declarations are refused before allocation with a
permanent unavailable status. A Docker-local file does not prove that a SLURM
node can use the image; qualify isolation and compute-node mounts before setting
these paths. No host-shell fallback is enabled.

The final dependency resolution includes all requested editable peer extras in
one solver call. This matters when corpus clients and documentation tools share
a dependency: OpenAlex's awscli needs an older docutils than the newest Sphinx.
The resolver chooses a mutually compatible Sphinx/plugin cohort before the final
consistency check. Successful individual installations do not establish that the
whole running environment is consistent.
