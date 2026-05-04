---
name: scitex-cloud
description: |
  [WHAT] SciTeX Cloud operational surface — 55 MCP tools across 6 categories — project_* (cloud project CRUD), repo_* (self-hosted Gitea clone/push/pull/PRs/issues), cloud_sdk_data/files/jobs_* (DataStore/FileVault/JobQueue SDK — submit compute jobs, upload/download files, CRUD records), api_* (Scholar paper search, CrossRef lookup, BibTeX enrichment, LaTeX compile via cloud), app_* (install/switch app plugins), onsite_* (in-browser Playwright on the live Django site).
  [WHEN] Use whenever the user asks to create a cloud project, push/clone via Gitea, submit a cloud job, upload to FileVault, compile LaTeX on cloud, search papers via Scholar, enrich BibTeX, switch app plugin, deploy to staging/production, or mentions SciTeX Cloud, Gitea, DataStore, FileVault, JobQueue, CloudClient.
  [HOW] `pip install scitex-cloud` then `import scitex_cloud`; see leaf skills for details.
tags: [scitex-cloud]
allowed-tools: mcp__scitex__cloud_*
primary_interface: mixed
interfaces:
  python: 1
  cli: 3
  mcp: 3
  skills: 2
  http: 2
---

# scitex-cloud Skill

> **Interfaces:** Python ⭐ · CLI ⭐⭐⭐ · MCP ⭐⭐⭐ · Skills ⭐⭐ · Hook — · HTTP ⭐⭐

> **Primary interfaces (two).** Both CLI and Python (or MCP) see heavy daily use — pick whichever fits the task.

`scitex-cloud` provides the operational surface for a SciTeX Cloud
deployment: a Django web platform, a `scitex-cloud` CLI, an MCP server
with ~55 tools, and a small Python API (`CloudClient`, `DockerManager`,
`health_check`, `get_environment`).

## Installation & import (two equivalent paths)

The same module is reachable via two install paths. Both forms work at
runtime; which one a user has depends on their install choice.

```python
# Standalone — pip install scitex-cloud
import scitex_cloud
scitex_cloud.CloudClient(...)

# Umbrella — pip install scitex
import scitex.cloud
scitex.cloud.CloudClient(...)
```

`pip install scitex-cloud` alone does NOT expose the `scitex` namespace;
`import scitex.cloud` raises `ModuleNotFoundError`. To use the
`scitex.cloud` form, also `pip install scitex`.

See [../../general/02_interface-python-api.md] for the ecosystem-wide
rule and empirical verification table.

## Sub-skills

### Mandatory leaves
- [01_installation.md](01_installation.md) — pip install + extras + smoke verify
- [02_quick-start.md](02_quick-start.md) — minimal create-project + push example
- [03_python-api.md](03_python-api.md) — top-level Python surface
- [04_cli-reference.md](04_cli-reference.md) — `scitex-cloud` subcommand summary
- [05_mcp-tools.md](05_mcp-tools.md) — ~55 MCP tools across 6 categories

### Core (06–09, 19)
- [06_python-api.md](06_python-api.md) — CloudClient, project_*, health_check (extended)
- [07_sdk.md](07_sdk.md) — Cloud SDK — DataStore, FileVault, JobQueue
- [08_project-management.md](08_project-management.md) — CLI project CRUD
- [09_app-management.md](09_app-management.md) — App plugins — init, validate, prefs, containers
- [19_gitea-cli.md](19_gitea-cli.md) — Gitea Git hosting — repos, PRs, issues, auth

### Workflows (10–19)
- [10_sync-architecture.md](10_sync-architecture.md) — Three-way sync — push/pull (git), sync-to/from (files)
- [11_deployment-staging.md](11_deployment-staging.md) — Deploy to staging — sync, build, verify
- [12_deployment-production.md](12_deployment-production.md) — Deploy to production — NAS safety, cgroup limits
- [13_scitex-deploy-staging.md](13_scitex-deploy-staging.md) — Legacy staging deploy recipe
- [14_scitex-deploy-prod.md](14_scitex-deploy-prod.md) — Legacy production deploy recipe
- [15_version-management.md](15_version-management.md) — Ecosystem version sync and bump
- [16_scitex-versions.md](16_scitex-versions.md) — Version-sync commands + Python API
- [17_scitex-versions-workflow.md](17_scitex-versions-workflow.md) — Bidirectional sync rules and workflow
- [18_scitex-versions-release.md](18_scitex-versions-release.md) — Version increment, tags, troubleshooting

### Standards (20–29)
- [21_refactoring-rules.md](21_refactoring-rules.md) — File size thresholds, extraction patterns
- [24_django-conventions.md](24_django-conventions.md) — 1:1:1:1 full-stack conventions, naming
- [22_cloud-refactor.md](22_cloud-refactor.md) — Refactor request template
- [23_mobile-testing.md](23_mobile-testing.md) — Mobile responsive testing — Playwright, viewport

### Architecture (30–39)
- [30_infrastructure.md](30_infrastructure.md) — Docker, setup, deploy, MCP server
- [31_development-environment.md](31_development-environment.md) — Docker dev setup, hot reload, access URLs
- [32_vite-frontend.md](32_vite-frontend.md) — Vite HMR, entry points, template tags

# EOF


## Environment

- [20_env-vars.md](20_env-vars.md) — SCITEX_* env vars read by scitex-cloud at runtime
