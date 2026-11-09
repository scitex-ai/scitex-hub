---
description: |
  [TOPIC] SciTeX Versions — Release, Tags, Environment & Troubleshooting
  [DETAILS] SciTeX Versions — Release, Tags, Environment & Troubleshooting.
tags: [scitex-hub-scitex-versions-release]
---
# SciTeX Versions — Release, Tags, Environment & Troubleshooting

## Hub release workflow

Use ordinary feature → `develop` → `main` pull requests, with required checks
passing on the exact release candidate. Do not push directly to either protected
branch. `main` is the stable release branch (see `CONTRIBUTING.md`).

The package version is declared in `pyproject.toml`; `scitex_hub.__version__`
reads installed distribution metadata, so there is no duplicate Python constant
to edit. Add matching release notes in `CHANGELOG.md`.

Regenerate the shipped `src/scitex_hub/_sphinx_html/` from the selected source
before accepting a version change. In the full documented dependency profile:

```bash
sphinx-build -W -d docs/sphinx/_build/doctrees -b html docs/sphinx docs/sphinx/_build/html
```

Replace the shipped HTML with that output and retain `.nojekyll`. Keep the
doctree cache outside the HTML bundle. Stage the bundle's public source-link
and theme assets through its narrow ignore exceptions; an untracked local
asset is not a reproducible release input. The version/help/Git-input controls in
`tests/config/test_shipped_documentation.py` reject a stale bundled version;
they do not validate every prose claim. A green docs job builds separate HTML
and does not establish that the committed wheel inputs were refreshed. The
develop-only bot commit can be refused by branch protection, so inspect the
actual bundle rather than relying on that best-effort delivery step.

Alpha versions use canonical PEP 440 spelling, for example package `0.22.0a0`
and tag `v0.22.0a0`. The human label “0.22.0-alpha” describes that same first
alpha; it is not an additional tag. Increment the alpha number for another
published alpha. Published tags are immutable: never delete, move, or force-push
one to repair a failed release.

After normal merge/review and successful release qualification, the authorized
release operator creates and pushes exactly the reviewed tag on the accepted
`main` commit. Do not push unrelated tags. The tag-driven workflow
`.github/workflows/pypi-publish-and-github-release-on-tag.yml` then:

1. Checks tag/package version equality and the checked-out Git commit.
2. Installs the full `.[all,dev]` dependencies and runs the PostgreSQL-backed
   Python 3.11/3.12/3.13 tests; an install failure cannot reduce that dependency set.
3. Builds wheel/sdist and publishes them through the configured PyPI OIDC job.
4. Creates the GitHub release; alpha/beta/RC versions are marked prereleases.
5. Opens a normal develop→main synchronization PR if still needed, leaving its
   checks/review/merge to the operator.

The tag workflow does not replace the normal TypeScript, security, import,
quality, and documentation checks. Require those on the accepted source before
creating a tag. A successful focused test or a deployed preview is not a full
release qualification. Manual workflow dispatch accepts an existing immutable
tag; inspect the original failure and public artifact availability before any
retry, rather than creating a second spelling of the same release.

## Inspect installed versions

Use `importlib.metadata.version("scitex-hub")` or `pip show scitex-hub` in the
specific environment being inspected. Source checkout versions, editable
metadata, and already-loaded worker code can differ; record each separately.

## Environment Paths
- **Local (WSL)**: `~/.env-3.11/bin/activate`
- **NAS**: `~/.venv-3.11/bin/activate`
- **Spartan**: `~/python3.11/bin/python3.11` (no venv, user-local install)

## Troubleshooting

### Merge conflicts on NAS/Spartan
**WARNING: ALWAYS check diff contents before discarding anything.**
```bash
# Step 1: READ what's there (MANDATORY)
scitex dev versions diff --host nas -p PACKAGE
# or: ssh nas "cd ~/proj/PACKAGE && git diff && git status"

# Step 2: Decide — is it improvement, artifact, or obsolete?

# Step 3a: If improvement → commit it first
scitex dev versions commit --host nas -p PACKAGE -m "preserve: work from NAS" --confirm

# Step 3b: If artifact/obsolete → safe to stash or discard
ssh nas "cd ~/proj/PACKAGE && git stash && git checkout develop && git pull && git stash pop"
# or if truly disposable (ONLY after reading contents):
# ssh nas "cd ~/proj/PACKAGE && git checkout -- . && git clean -fd && git pull"
```

### Check installed version
```bash
pip show PACKAGE | grep Version
```

### Stale dist-info directories
If `importlib.metadata` reports wrong version (e.g., old version instead of current):
```bash
# Find all dist-info for the package
ls ~/.env-3.11/lib/python3.11/site-packages/PACKAGE_NAME-*.dist-info
# Remove stale ones (keep only the current version)
rm -rf ~/.env-3.11/lib/python3.11/site-packages/PACKAGE_NAME-OLD_VERSION.dist-info
```

## See also
- [16_scitex-versions.md](16_scitex-versions.md) — Commands reference and Python API
- [17_scitex-versions-workflow.md](17_scitex-versions-workflow.md) — Bidirectional sync rules and workflow
