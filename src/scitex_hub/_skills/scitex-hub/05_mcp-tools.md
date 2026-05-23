---
description: |
  [TOPIC] scitex-hub MCP Tools
  [DETAILS] ~55 MCP tools across 6 categories — project_*, repo_*, cloud_sdk_data/files/jobs_*, api_*, app_*, onsite_* — exposed to AI agents via `scitex-hub-mcp` (stdio).
tags: [scitex-hub-mcp-tools]
---

# MCP Tools

`scitex-hub` ships ~55 MCP tools, exposed via the `scitex-hub-mcp`
stdio server (or `scitex-hub mcp start`). Tool names are namespaced
under `mcp__scitex__cloud_*`.

## Categories

| Prefix              | Purpose                                                |
|---------------------|--------------------------------------------------------|
| `cloud_project_*`   | Project CRUD (create / list / switch / rename / delete)|
| `cloud_repo_*`      | Self-hosted Gitea — clone / push / pull / PRs / issues |
| `cloud_cloud_sdk_data_*`  | DataStore — CRUD records (create / get / update / delete / list / search) |
| `cloud_cloud_sdk_files_*` | FileVault — upload / download / list / delete    |
| `cloud_cloud_sdk_jobs_*`  | JobQueue — submit / status / list / cancel       |
| `cloud_api_*`       | Scholar search, CrossRef lookup, BibTeX enrichment, LaTeX compile via cloud |
| `cloud_app_*`       | App plugin install / switch / prefs / containers       |
| `cloud_onsite_*`    | In-browser Playwright on the live Django site          |

## Starting the server

```bash
scitex-hub-mcp                # stdio server (Claude Desktop)
scitex-hub serve -t sse       # SSE (remote)
```

## Discoverability from inside Claude

Each tool has a JSONSchema input — list all with the MCP `list-tools`
call. The `scitex-dev` MCP also surfaces a `skills_list` /
`skills_get` for these docs.

## See also

- `06_python-api.md` — `CloudClient` (the Python equivalent of `cloud_api_*`)
- `07_sdk.md` — DataStore / FileVault / JobQueue SDK (Python equivalent of `cloud_cloud_sdk_*`)
- `08_project-management.md` — project_* CLI semantics
- `19_gitea-cli.md` — repo_* CLI semantics
