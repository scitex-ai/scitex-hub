---
description: |
  [TOPIC] scitex-hub CLI Reference
  [DETAILS] Top-level subcommands of `scitex-hub` — project, push/pull, workspace push/pull/status, deploy, docker, gitea, sdk, app, mcp, etc.
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
| `project`        | Manage SciTeX Hub projects                         |
| `push-project`   | `git push` to Gitea (committed changes)              |
| `pull-project`   | `git pull` from Gitea (committed changes)            |
| `gitea`          | Gitea operations (wraps `tea` CLI)                   |

## Sync (workspace, Dropbox-style)

| Command            | Purpose                                                |
|--------------------|--------------------------------------------------------|
| `workspace push`   | Sync working files to workspace                        |
| `workspace pull`   | Sync working files from workspace                      |
| `workspace status` | Show sync state across Local / Gitea / Workspace       |
| `workspace`        | Workspace operations (upload, push/pull, list, sync)   |

The old spellings `sync-to` / `sync-from` / `sync-status` / `ss` are
deprecated warn-phase aliases (removed in v0.20).

## Deploy / containers / init

| Command   | Purpose                                                       |
|-----------|---------------------------------------------------------------|
| `deploy`  | Deploy SciTeX Hub (was `deploy-project`, deprecated)          |
| `init`    | Initialize the environment (was `setup-environment`)          |
| `docker`  | Docker container management                                   |
| `status`  | Show deployment status (was `show-status`, deprecated)        |
| `logs`    | Show container logs (was `show-logs`, deprecated)             |
| `context` | Web app context for AI agents                                 |

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
scitex-hub init --env dev
scitex-hub project create my-paper
scitex-hub push-project
scitex-hub workspace push
scitex-hub docker up
scitex-hub mcp start
```

See workflow leaves (`08_project-management.md`, `19_gitea-cli.md`,
`11_deployment-staging.md`, `12_deployment-production.md`) for option-level
detail.
