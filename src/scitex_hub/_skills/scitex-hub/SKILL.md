---
name: scitex-hub
description: |
  Operate and validate SciTeX Hub projects, hosting, leaf GUI plugins,
  cloud jobs and deployment. Start with the relevant workflow below,
  verify the actual code/runtime and authorized scope, then choose an
  API, CLI, MCP or HTTP interface. Keep application behavior in its leaf.
tags: [scitex-hub]
allowed-tools: mcp__scitex__cloud_*
primary_interface: mixed
interfaces:
  python: 1
  cli: 3
  mcp: 3
  skills: 2
  http: 2
---

# scitex-hub Skill

> **Interfaces:** Python ⭐ · CLI ⭐⭐⭐ · MCP ⭐⭐⭐ · Skills ⭐⭐ · Hook — · HTTP ⭐⭐

Begin with the relevant workflow below. It defines ownership, prerequisites,
validation, and completion; then choose Python, CLI, MCP, or HTTP for its steps.
Skill first means loading that workflow before choosing an interface.

`scitex-hub` provides the operational surface for a SciTeX Hub
deployment: a Django web platform, a `scitex-hub` CLI, an MCP server
and a small Python API (`CloudClient`, `DockerManager`,
`health_check`, `get_environment`).

## Installation & import (two equivalent paths)

The same module is reachable via two install paths. Both forms work at
runtime; which one a user has depends on their install choice.

```python
# Standalone — pip install scitex-hub
import scitex_hub
scitex_hub.CloudClient(...)

# Umbrella — pip install scitex
import scitex.cloud
scitex.cloud.CloudClient(...)
```

`pip install scitex-hub` alone does NOT expose the `scitex` namespace;
`import scitex.cloud` raises `ModuleNotFoundError`. To use the
`scitex.cloud` form, also `pip install scitex`.

## Sub-skills

### Mandatory leaves
- [01_installation.md](01_installation.md) — pip install + extras + smoke verify
- [02_quick-start.md](02_quick-start.md) — minimal create-project + push example
- [03_python-api.md](03_python-api.md) — top-level Python surface
- [04_cli-reference.md](04_cli-reference.md) — `scitex-hub` subcommand summary
- [05_mcp-tools.md](05_mcp-tools.md) — MCP interfaces; check the running server's registrations

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
- [22_hub-refactor.md](22_hub-refactor.md) — Refactor request template
- [23_mobile-testing.md](23_mobile-testing.md) — Mobile responsive testing — Playwright, viewport

### Architecture (30–39)
- [30_infrastructure.md](30_infrastructure.md) — Docker, setup, deploy, MCP server
- [31_development-environment.md](31_development-environment.md) — Docker dev setup, hot reload, access URLs
- [32_vite-frontend.md](32_vite-frontend.md) — Vite HMR, entry points, template tags
- [35_clew-cloud-store.md](35_clew-cloud-store.md) — private Clew web stores, request scoping, synthetic end-to-end tests, and deployment limits
- [36_leaf-gui-ownership.md](36_leaf-gui-ownership.md) — SDK boundaries and migration quality gates
- [37_maintenance-mode.md](37_maintenance-mode.md) — request admission, trusted local state, and explicit job-draining limits

### User runbooks (40–49)
- [40_user-publish-runbook.md](40_user-publish-runbook.md) — End-to-end USER walkthrough: PAT login → `project create --category app` → `app submit` → hub listing (agent-flow lives in a separate skill)

# EOF


## Environment

- [20_env-vars.md](20_env-vars.md) — SCITEX_* env vars read by scitex-hub at runtime
