---
description: |
  [TOPIC] scitex-hub CLI Reference
  [DETAILS] Top-level subcommands of `scitex-hub` — project, push/pull, sync-to/from, deploy, docker, gitea, sdk, app, mcp, etc.
tags: [scitex-hub-cli-reference]
---

# CLI Reference

`scitex-hub` is the entry point installed by `pip install scitex-hub`.

## Top-level options

| Flag                | Purpose                                          |
|---------------------|--------------------------------------------------|
| `-V / --version`    | Show version and exit                            |
| `--help-recursive`  | Show help for the root and every subcommand      |
| `-h / --help`       | Show help                                        |

## Project / repo

| Command          | Purpose                                              |
|------------------|------------------------------------------------------|
| `project`        | Manage SciTeX Cloud projects                         |
| `push-project`   | `git push` to Gitea (committed changes)              |
| `pull-project`   | `git pull` from Gitea (committed changes)            |
| `gitea`          | Gitea operations (wraps `tea` CLI)                   |

## Sync (workspace, Dropbox-style)

| Command        | Purpose                                                |
|----------------|--------------------------------------------------------|
| `sync-to`      | Sync working files to workspace                        |
| `sync-from`    | Sync working files from workspace                      |
| `sync-status`  | Show sync state across Local / Gitea / Workspace       |
| `ss`           | Alias for `sync-status`                                |
| `workspace`    | Workspace operations (upload, sync, list projects)     |

## Deploy / containers / setup

| Command              | Purpose                                            |
|----------------------|----------------------------------------------------|
| `deploy-project`     | Deploy SciTeX Cloud                                |
| `setup-environment`  | Setup SciTeX Cloud environment                     |
| `docker`             | Docker container management                        |
| `show-status`        | Show deployment status                             |
| `show-logs`          | Show container logs                                |
| `context`            | Web app context for AI agents                      |

## SDK / app plugins / MCP

| Command            | Purpose                                              |
|--------------------|------------------------------------------------------|
| `sdk`              | Platform SDK — DataStore, FileVault, JobQueue        |
| `app`              | Manage SciTeX app plugins                            |
| `mcp`              | MCP (Model Context Protocol) server commands         |
| `skills`           | View package skills (workflow-oriented guides)       |
| `completion`       | Shell tab-completion commands                        |
| `list-python-apis` | List Python APIs                                     |

## Examples

```bash
scitex-hub setup-environment --env dev
scitex-hub project create my-paper
scitex-hub push-project
scitex-hub sync-to
scitex-hub docker up
scitex-hub mcp start
```

See workflow leaves (`08_project-management.md`, `19_gitea-cli.md`,
`11_deployment-staging.md`, `12_deployment-production.md`) for option-level
detail.
