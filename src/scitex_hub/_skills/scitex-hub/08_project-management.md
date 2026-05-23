---
description: |
  [TOPIC] Project Management CLI
  [DETAILS] CLI commands for SciTeX Cloud project CRUD — create, list, delete, rename. Each project gets a Gitea repo + Django project + workspace directory..
tags: [scitex-hub-project-management]
---

# Project Management CLI

## Commands

```bash
scitex-hub project create <name> [-d "description"] [-t template]
scitex-hub project list [--json]
scitex-hub project delete <slug> [--yes]
scitex-hub project rename <slug> <new-name>
```

## Options

### project create
| Option | Default | Description |
|--------|---------|-------------|
| `name` | (required) | Project name |
| `-d / --description` | `""` | Short description |
| `-t / --template` | `scitex_minimal` | Template ID |

Creates in one step: Gitea repository + Django project record + workspace directory.

### project list
| Option | Default | Description |
|--------|---------|-------------|
| `--json` | (flag) | Output as JSON |

### project delete
| Option | Default | Description |
|--------|---------|-------------|
| `slug` | (required) | URL-safe project name |
| `--yes` | (flag) | Skip confirmation prompt |

### project rename
| Option | Default | Description |
|--------|---------|-------------|
| `slug` | (required) | Current URL-safe name |
| `new-name` | (required) | New project name |

## Python API

```python
from scitex_hub.project import project_list, project_create, project_delete, project_rename

projects = project_list()
# -> [{"id": "abc123", "name": "my-project", "description": "...", "created_at": "...", "updated_at": "..."}, ...]

result = project_create("my-research", description="Paper on X", template="scitex_minimal")
# -> {"project_id": "abc123", "name": "my-research", "success": True}

project_delete("my-research")   # raises RuntimeError on failure

project_rename("my-research", "my-research-v2")
```

## MCP Tools

| Tool | What it does |
|------|-------------|
| `cloud_project_create` | Create project (Gitea + workspace) |
| `cloud_project_list` | List all projects |
| `cloud_project_delete` | Delete project by slug |
| `cloud_project_rename` | Rename project |
| `cloud_project_switch` | Switch active project context |

## Examples

```bash
# Create and verify
scitex-hub project create neural-dynamics -d "Spiking network paper"
scitex-hub project list

# Rename then delete
scitex-hub project rename neural-dynamics neural-dynamics-v2
scitex-hub project delete neural-dynamics-v2 --yes
```

# EOF
