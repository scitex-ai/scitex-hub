---
description: |
  [TOPIC] SciTeX Versions Management
  [DETAILS] SciTeX Versions Management.
tags: [scitex-cloud-scitex-versions]
---
# SciTeX Versions Management

## Overview
Manage and sync versions across the SciTeX ecosystem packages on local and remote hosts.
Syncing is **bidirectional**: local → remote (push) and remote → local (pull).

## Dashboard
Check this first:
scitex dev versions list --json
http://127.0.0.1:5000

## Ecosystem Packages (in order)
01. scitex (scitex-python)
02. scitex-cloud
03. figrecipe
04. openalex-local
05. crossref-local
06. scitex-writer
07. scitex-dataset
08. socialia
09. automated-research-demo
10. scitex-research-template
11. pip-project-template
12. singularity-template
... and being cumulated


## PyPI Trusted Publisher

Configure github action in this pattern

``` bash
Repository: ywatanabe1989/figrecipe
Workflow: publish-pypi.yml
Environment name: pypi
```

## Commands

### List versions (read-only)
```bash
scitex dev versions list                         # Local + PyPI versions
scitex dev versions list --json                  # JSON output
scitex dev versions list -p scitex               # Specific package
scitex dev versions list --local-only            # Skip PyPI
scitex dev versions list-hosts                   # SSH host versions
scitex dev versions list-hosts --host nas        # Specific host
scitex dev versions list-remotes                 # GitHub remote versions
scitex dev versions list-rtd                     # Read the Docs status
scitex dev versions check                        # Consistency check
scitex dev versions dashboard                    # Start dashboard GUI
scitex dev versions dashboard --background       # Run as background daemon
scitex dev versions dashboard --stop             # Stop background daemon
scitex dev versions dashboard --no-browser       # Don't open browser
```

### Sync: Local → Remote (push)
```bash
# Remote host sync
scitex dev versions sync                             # Preview (dry run)
scitex dev versions sync --confirm                   # Execute (parallel)
scitex dev versions sync --confirm --host nas        # Sync specific host
scitex dev versions sync --confirm -p scitex         # Sync specific package
scitex dev versions sync --confirm --no-install      # Git pull only

# Local install
scitex dev versions sync --local                     # Preview local install
scitex dev versions sync --local --confirm           # Execute local install

# Tag push
scitex dev versions sync --tags                      # Preview tag push
scitex dev versions sync --tags --confirm            # Execute tag push
```

### Sync: Remote → Local (pull)
```bash
# Check what changed on remote hosts
scitex dev versions diff                             # Show diffs on all hosts
scitex dev versions diff --host nas                  # Specific host
scitex dev versions diff -p scitex                   # Specific package
scitex dev versions diff --json                      # JSON output

# Commit remote changes and push to origin
scitex dev versions commit --host nas                # Preview (dry run)
scitex dev versions commit --host nas --confirm      # Execute commit + push
scitex dev versions commit --host nas -m "fix: msg"  # Custom commit message
scitex dev versions commit --host nas --no-push      # Commit only, no push

# Pull from origin to local
scitex dev versions pull                             # Preview (dry run)
scitex dev versions pull --confirm                   # Execute git pull
scitex dev versions pull -p scitex --confirm         # Specific package
scitex dev versions pull --no-stash                  # Don't stash dirty repos
```

### MCP Tools
```
# Read-only
mcp__scitex__dev_versions_list
mcp__scitex__dev_config_show

# Local → Remote (push)
mcp__scitex__dev_versions_sync        # confirm=False → preview, confirm=True → execute
mcp__scitex__dev_versions_sync_local  # confirm=False → preview, confirm=True → execute

# Remote → Local (pull)
mcp__scitex__dev_versions_diff        # read-only: show remote diffs
mcp__scitex__dev_versions_commit      # confirm=False → preview, confirm=True → execute
mcp__scitex__dev_versions_pull        # confirm=False → preview, confirm=True → execute

# Other
mcp__scitex__dev_bulk_rename          # confirm=False → preview, confirm=True → execute
mcp__scitex__dev_test_local
mcp__scitex__dev_test_hpc
mcp__scitex__dev_test_hpc_poll
mcp__scitex__dev_test_hpc_result
```

### Python API
```python
from scitex._dev import sync_all, sync_local, sync_tags
from scitex._dev import remote_diff, remote_commit, pull_local

# Local → Remote (preview by default)
preview = sync_all()                          # dry run
results = sync_all(confirm=True)              # parallel across hosts
results = sync_all(hosts=["nas"], confirm=True)
results = sync_local(confirm=True)
results = sync_tags(confirm=True)

# Remote → Local (preview by default)
diffs = remote_diff()                         # read-only
diffs = remote_diff(host="nas", packages=["scitex"])
results = remote_commit(host="nas", confirm=True)
results = pull_local(confirm=True)
results = pull_local(confirm=True, stash=True)  # auto-stash dirty repos
```

## See also
- [17_scitex-versions-workflow.md](17_scitex-versions-workflow.md) — Bidirectional sync rules and workflow
- [18_scitex-versions-release.md](18_scitex-versions-release.md) — Version increment, tag syncing, environment paths, troubleshooting
