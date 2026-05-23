---
description: |
  [TOPIC] SciTeX Versions — Release, Tags, Environment & Troubleshooting
  [DETAILS] SciTeX Versions — Release, Tags, Environment & Troubleshooting.
tags: [scitex-hub-scitex-versions-release]
---
# SciTeX Versions — Release, Tags, Environment & Troubleshooting

## Version Increment Workflow

### 0. Major, minor, and patch

We use version in the form of vX.Y.Z, where

X is Major
Y is Minor
Z is Patch and may have -alpha, -beta suffix

When increment version, check the difference and determine if it is minor or patch. No major update please as long as user explicitly requests.

### 1. Update version in pyproject.toml
```bash
# Edit pyproject.toml: version = "X.Y.Z"
```

### 2. Commit and tag
```bash
git add pyproject.toml
git commit -m "chore: bump version to X.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin develop --tags
```

### 3. Sync to all hosts
```bash
scitex dev versions sync --tags --confirm
scitex dev versions sync --confirm
```

## Tag Syncing

### Fix tag not reachable from current branch
When `git describe --tags` shows an older tag because the latest tag is on a different branch (e.g., main vs develop):
```bash
cd ~/proj/PACKAGE
git tag -d vX.Y.Z                           # Delete local tag
git tag -a vX.Y.Z -m "Release vX.Y.Z" HEAD  # Retag on current HEAD
git push origin vX.Y.Z --force               # Force-push updated tag
```

### Sync all tags from remote
```bash
cd ~/proj/PACKAGE && git fetch --tags
```

### Push all local tags to remote
```bash
cd ~/proj/PACKAGE && git push origin --tags
```

### List tags sorted by version
```bash
cd ~/proj/PACKAGE && git tag --sort=-v:refname | head -10
```

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
