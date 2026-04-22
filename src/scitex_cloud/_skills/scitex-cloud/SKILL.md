---
description: SciTeX Cloud platform — Django web app + CLI + MCP server + Python SDK. Covers project management, Git hosting (Gitea), three-way sync, app deployment, DataStore/FileVault/JobQueue SDK, and infrastructure. Use when managing cloud projects, syncing code, deploying apps, or running cloud operations.
allowed-tools: Bash, Read, Grep, Glob
---

# scitex-cloud Skill

## What this package is

`scitex-cloud` provides the operational surface for a SciTeX Cloud
deployment. It ships:

- A **Django web platform** (under `apps/`) with Scholar, Writer,
  FigRecipe, Console, Hub, Clew modules — run with
  `make start` / `make ENV=prod start`.
- A **CLI** (`scitex-cloud`) covering project management, Gitea Git
  hosting, sync, docker, deploy, MCP, workspace, SDK, and status.
- An **MCP server** (`scitex-cloud-mcp` / `scitex-cloud mcp start`)
  exposing ~55 tools across 6 categories for AI agents.
- A small **Python API** (`CloudClient`, `health_check`,
  `get_environment`, `DockerManager`).

## Installation

```bash
pip install scitex-cloud               # CLI only
pip install scitex-cloud[mcp]          # CLI + MCP server
pip install scitex-cloud[all]          # Everything (django, test, gui, mcp, dev)
# Development:
pip install -e /home/ywatanabe/proj/scitex-cloud
```

## CLI surface (actual, from `src/scitex_cloud/_cli/main.py`)

Top-level command groups registered on `main`:

| Command | Module | Notes |
|---------|--------|-------|
| `app` | `_cli/app.py` | App plugin scaffolding |
| `setup` | `_cli/setup.py` | Environment setup |
| `deploy` | `_cli/deploy.py` | Deploy helpers |
| `docker` | `_cli/docker.py` | Container mgmt |
| `gitea` | `_cli/gitea.py` | Gitea Git hosting (repos, PRs, issues, auth) |
| `mcp` | `_cli/mcp.py` | `start`, `list-tools`, `doctor`, `installation` |
| `context` | `_cli/context.py` | Context group |
| `status` / `logs` | `_cli/status.py` | Deployment status + logs |
| `completion` | `_cli/completion.py` | Shell completion |
| `workspace` | `_cli/workspace.py` | Workspace auth + commands |
| `sdk` | `_cli/sdk.py` | SDK subcommands |
| `project` | `_cli/project.py` | Project CRUD |
| `skills` | `scitex_dev` plugin | Registered when `scitex-dev` is installed |

Use `scitex-cloud --help-recursive` to list every sub-command.

## MCP tools (actual, from `src/scitex_cloud/_mcp_tools/`)

| Category | Tools | File |
|----------|-------|------|
| gitea | 14 | `_mcp_tools/gitea.py` |
| sdk | 14 | `_mcp_tools/sdk.py` |
| api | 9 | `_mcp_tools/api.py` |
| app | 7 | `_mcp_tools/app.py` |
| onsite | 6 | `_mcp_tools/onsite.py` |
| project_crud | 5 | `_mcp_tools/project_crud.py` |

Registration: `_mcp_tools/__init__.py::register_all_tools`.
Entry point: `scitex-cloud-mcp` → `scitex_cloud._mcp_server:main`.

## Python API (actual, from `src/scitex_cloud/__init__.py`)

```python
import scitex_cloud

scitex_cloud.__version__
scitex_cloud.get_version()
scitex_cloud.health_check(endpoint=None)       # local or remote
client = scitex_cloud.CloudClient()            # from _api.py
env = scitex_cloud.get_environment()           # from _config/_environments.py
docker = scitex_cloud.DockerManager()          # from _utils/_docker.py
```

## Sub-skill files

| File | Topic |
|------|-------|
| [python-api.md](python-api.md) | CloudClient, project_*, health_check |
| [project-management.md](project-management.md) | CLI project CRUD — create, list, delete, rename |
| [sync-architecture.md](sync-architecture.md) | Three-way sync — push/pull (git) and sync-to/from (files) |
| [gitea-cli.md](gitea-cli.md) | Gitea Git hosting — repos, PRs, issues, auth |
| [app-management.md](app-management.md) | App plugins — init, validate, submit, prefs, containers |
| [sdk.md](sdk.md) | Cloud SDK — DataStore, FileVault, JobQueue |
| [infrastructure.md](infrastructure.md) | Docker, setup, deploy, MCP server |
| [deployment-staging.md](deployment-staging.md) | Deploy to staging — sync, build, verify |
| [deployment-production.md](deployment-production.md) | Deploy to production — NAS safety, cgroup limits |
| [scitex-deploy-staging.md](scitex-deploy-staging.md) | Legacy staging deploy recipe |
| [scitex-deploy-prod.md](scitex-deploy-prod.md) | Legacy production deploy recipe |
| [scitex-cloud-stage.md](scitex-cloud-stage.md) | Ecosystem staging prerequisites |
| [ship-scitex-cloud.md](ship-scitex-cloud.md) | Ship-to-prod one-liner recipe |
| [version-management.md](version-management.md) | Ecosystem version sync and bump |
| [scitex-versions.md](scitex-versions.md) | Detailed version-sync walkthrough (bidirectional) |
| [refactoring-rules.md](refactoring-rules.md) | File size thresholds, extraction patterns |
| [cloud-refactor.md](cloud-refactor.md) | Refactor request template |
| [development-environment.md](development-environment.md) | Docker dev setup, hot reload, access URLs |
| [django-conventions.md](django-conventions.md) | 1:1:1:1 full-stack conventions, naming |
| [vite-frontend.md](vite-frontend.md) | Vite HMR, entry points, template tags |
| [mobile-testing.md](mobile-testing.md) | Mobile responsive testing — Playwright, viewport, auth selectors |

## Quick navigation

- Managing cloud projects → [project-management.md](project-management.md)
- Syncing code between local/workspace → [sync-architecture.md](sync-architecture.md)
- Git repo operations (clone, fork, PR, issue) → [gitea-cli.md](gitea-cli.md)
- Developing/publishing apps → [app-management.md](app-management.md)
- DataStore / FileVault / JobQueue → [sdk.md](sdk.md)
- Docker, deploy, MCP server → [infrastructure.md](infrastructure.md)
- Python API programmatic access → [python-api.md](python-api.md)
- Deploy to staging → [deployment-staging.md](deployment-staging.md)
- Deploy to production → [deployment-production.md](deployment-production.md)
- Version sync across ecosystem → [version-management.md](version-management.md) / [scitex-versions.md](scitex-versions.md)
- Refactoring rules → [refactoring-rules.md](refactoring-rules.md)
- Dev environment setup → [development-environment.md](development-environment.md)
- Django conventions (1:1:1:1) → [django-conventions.md](django-conventions.md)
- Vite/TypeScript frontend → [vite-frontend.md](vite-frontend.md)
- Mobile responsive testing → [mobile-testing.md](mobile-testing.md)

# EOF
