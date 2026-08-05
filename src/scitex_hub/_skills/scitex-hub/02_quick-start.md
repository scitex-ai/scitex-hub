---
description: |
  [TOPIC] scitex-hub Quick Start
  [DETAILS] Smallest useful example — create a cloud project and push code via the CLI; equivalent Python via CloudClient.
tags: [scitex-hub-quick-start]
---

# Quick Start

## CLI: create project, push, check status

```bash
scitex-hub project create my-project
scitex-hub push-project           # push current dir to Gitea
scitex-hub status
```

Project state lives under `~/.scitex/hub/projects/<name>/` and on the
remote Gitea instance configured in `~/.scitex/hub/config.yaml`.

## Python: CloudClient

```python
import scitex_hub

client = scitex_hub.CloudClient()
print(scitex_hub.health_check())          # local package info
print(client.scholar_search("hippocampus")) # via cloud Scholar API
```

## Sync workflows

```bash
scitex-hub workspace push      # push working files (Dropbox-style)
scitex-hub workspace pull     # pull working files
scitex-hub workspace status  # 3-way: Local / Gitea / Workspace
```

## Next steps

- `04_cli-reference.md` — full CLI summary
- `06_python-api.md` — Python surface
- `07_sdk.md` — DataStore / FileVault / JobQueue SDK
- `08_project-management.md` — project lifecycle
- `19_gitea-cli.md` — Git hosting commands
- `10_sync-architecture.md` — three-way sync details
