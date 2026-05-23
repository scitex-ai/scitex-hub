---
description: |
  [TOPIC] scitex-cloud Python API
  [DETAILS] Top-level public callables — CloudClient, Environment, get_environment, DockerManager, get_version, health_check.
tags: [scitex-cloud-python-api]
---

# Python API

Top-level public surface re-exported from `scitex_hub`.

## Public symbols

| Name              | Purpose                                                    |
|-------------------|------------------------------------------------------------|
| `__version__`     | Installed package version                                  |
| `get_version()`   | Same as `__version__` (callable form)                      |
| `health_check()`  | Local package info or remote endpoint health (HTTP GET)    |
| `CloudClient`     | Main facade — Scholar, BibTeX, project, repo, sdk          |
| `Environment`     | Enum-like environment descriptor (dev / staging / prod)    |
| `get_environment()` | Resolve current `Environment` from env vars / config     |
| `DockerManager`   | Docker container helper (start/stop/logs)                  |

## Example

```python
import scitex_hub

print(scitex_hub.health_check())          # local package info
print(scitex_hub.health_check("https://cloud.scitex.ai/health"))

env = scitex_hub.get_environment()
print(env)

client = scitex_hub.CloudClient()
papers = client.scholar_search("phase-amplitude coupling")
```

## Beyond the top level

- `06_python-api.md` — extended `CloudClient` reference + project_*
- `07_sdk.md` — DataStore / FileVault / JobQueue SDK
- `09_app-management.md` — App plugin SDK

The MCP tool layer wraps the same calls for AI agents — see
`05_mcp-tools.md`.
